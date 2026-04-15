from app.rag.vector_store import VectorStore
from app.graph.neo4j_client import Neo4jClient


# Simple placeholder embedding function (returns zero vector)
def _dummy_embed(text: str) -> list[float]:
    return [0.0] * 768


"""GraphRAG – hybrid retrieval from Milvus (semantic) + Neo4j (structural).

The query flow:
1. Embed the natural‑language *question* using the configured vLLM embedding model.
2. Perform an ANN search in Milvus to obtain the most similar stored vectors.
3. For each hit, extract the associated entity identifier from the metadata.
4. Query Neo4j for those entities (including their type and direct relationships).
5. Assemble a concise textual answer summarising the findings.

If any step fails, the function degrades gracefully:
- Missing embeddings → zero‑vector search (fallback already handled in VectorStore).
- No Milvus hits → simple fallback response.
- Neo4j query errors are logged and ignored for that hit.
"""

from ..core.embedding import EmbeddingModel
from .vector_store import VectorStore
from ..graph.neo4j_client import Neo4jClient
from ..core.logger import get_logger

_logger = get_logger(__name__)


def graphrag_query(question: str, top_k: int = 5) -> str:
    """Execute a GraphRAG query.

    Parameters
    ----------
    question: str
        Natural‑language query from the user.
    top_k: int, optional
        Number of nearest‑vector hits to retrieve from Milvus (default 5).

    Returns
    -------
    str
        Human‑readable summary of matched entities and their relationships.
    """
    # 1️⃣ Embed the question
    embedder = EmbeddingModel()
    try:
        embed_vecs = embedder.embed([question])
        if not embed_vecs:
            raise RuntimeError("Empty embedding result")
        query_vec = embed_vecs[0]
    except Exception as e:
        _logger.error(f"Embedding step failed: {e}")
        # Fallback to zero‑vector (handled by VectorStore internally)
        query_vec = [0.0] * embedder.dim

    # 2️⃣ Milvus similarity search
    store = VectorStore()
    try:
        hits = store.search(query_vec, top_k=top_k)
    except Exception as e:
        _logger.error(f"Milvus search failed: {e}")
        hits = []

    if not hits:
        _logger.info("Milvus returned no hits; returning fallback response.")
        return f"No relevant knowledge graph entries found for: {question}"

    # 3️⃣ Decide routing (graph / vector) via LLMRouter
    from .router import LLMRouter
    router = LLMRouter()
    decision = router.route(question)
    # If vector retrieval is disabled, skip Milvus hits (already obtained but ignore)
    if not decision.get("vector", True):
        _logger.info("Router decided to skip vector search – returning fallback response.")
        return f"Vector search disabled for query: {question}"

    # 4️⃣ Neo4j retrieval for each hit – only if graph flag true
    result_chunks = []
    if decision.get("graph", True):
        neo = Neo4jClient()
        for key, distance, meta in hits:
            entity_name = meta.get("entity_name") or meta.get("key") or str(key)
            try:
                # Heuristic: if question contains multi‑hop keywords, use variable‑length path query
                lower_q = question.lower()
                multi_hop = any(tok in lower_q for tok in ["上级的上级", "上上级", "上级的上级的上级", "上2级", "ancestor", "superior"])
                if multi_hop:
                    # Variable‑length path: min 2 hops, max 3 (configurable)
                    path_results = neo.variable_path_query(start_name=entity_name, min_hops=2, max_hops=3)
                    for path_info in path_results:
                        path = " -> ".join(path_info.get("path", []))
                        rels = ", ".join(path_info.get("relations", []))
                        snippet = (
                            f"Path '{path}' (relations: {rels}) – similarity: {distance:.2f}"
                        )
                        result_chunks.append(snippet)
                    continue  # skip exact/full‑text when multi‑hop handled

                # Exact match first
                cypher = """
                MATCH (e:Entity {name: $name})
                OPTIONAL MATCH (e)-[r]->(connected)
                RETURN e.type AS type, collect({
                    rel_type: type(r),
                    target: connected.name,
                    target_type: connected.type
                }) AS relations
                """
                records = neo.run(cypher, {"name": entity_name})
                if records:
                    for rec in records:
                        ent_type = rec.get("type")
                        rels = rec.get("relations") or []
                        rel_str = ", ".join(
                            f"{r['rel_type']} -> {r['target']} ({r['target_type']})"
                            for r in rels
                        )
                        snippet = (
                            f"Entity '{entity_name}' (type: {ent_type}) "
                            + (
                                f"with relations: {rel_str}" if rel_str else "has no outgoing relations"
                            )
                            + f" – similarity score: {distance:.2f}"
                        )
                        result_chunks.append(snippet)
                    continue  # exact match succeeded, skip full‑text fallback

                # Full‑text fallback (fuzzy match)
                ft_hits = neo.fulltext_search(entity_name)
                for ft in ft_hits:
                    props = ft.get("properties", {})
                    ft_name = props.get("name")
                    if not ft_name:
                        continue
                    sub_cypher = """
                    MATCH (e:Entity {name: $ft_name})
                    OPTIONAL MATCH (e)-[r]->(connected)
                    RETURN e.type AS type, collect({
                        rel_type: type(r),
                        target: connected.name,
                        target_type: connected.type
                    }) AS relations
                    """
                    sub_records = neo.run(sub_cypher, {"ft_name": ft_name})
                    for rec in sub_records:
                        ent_type = rec.get("type")
                        rels = rec.get("relations") or []
                        rel_str = ", ".join(
                            f"{r['rel_type']} -> {r['target']} ({r['target_type']})"
                            for r in rels
                        )
                        snippet = (
                            f"Entity '{ft_name}' (type: {ent_type}) "
                            + (
                                f"with relations: {rel_str}" if rel_str else "has no outgoing relations"
                            )
                            + f" – similarity score: {distance:.2f} (ft score: {ft.get('score'):.2f})"
                        )
                        result_chunks.append(snippet)
            except Exception as e:
                _logger.error(f"Neo4j query failed for entity '{entity_name}': {e}")
                continue
    else:
        _logger.info("Router decided to skip graph lookup – returning vector‑only results.")
        # Build simple snippets from vector hits only
        for key, distance, meta in hits:
            name = meta.get("entity_name") or meta.get("key") or str(key)
            snippet = f"Vector hit '{name}' – similarity score: {distance:.2f}"
            result_chunks.append(snippet)
                # Retrieve the entity type for the fuzzy‑matched node
                sub_cypher = """
                MATCH (e:Entity {name: $ft_name})
                OPTIONAL MATCH (e)-[r]->(connected)
                RETURN e.type AS type, collect({
                    rel_type: type(r),
                    target: connected.name,
                    target_type: connected.type
                }) AS relations
                """
                sub_records = neo.run(sub_cypher, {"ft_name": ft_name})
                for rec in sub_records:
                    ent_type = rec.get("type")
                    rels = rec.get("relations") or []
                    rel_str = ", ".join(
                        f"{r['rel_type']} -> {r['target']} ({r['target_type']})"
                        for r in rels
                    )
                    snippet = (
                        f"Entity '{ft_name}' (type: {ent_type}) "
                        + (
                            f"with relations: {rel_str}"
                            if rel_str
                            else "has no outgoing relations"
                        )
                        + f" – similarity score: {distance:.2f} (ft score: {ft.get('score'):.2f})"
                    )
                    result_chunks.append(snippet)
        except Exception as e:
            _logger.error(f"Neo4j query failed for entity '{entity_name}': {e}")
            continue

    if not result_chunks:
        return f"No graph structures could be retrieved for: {question}"

    # 5️⃣ Assemble final answer
    header = f"GraphRAG results for query: '{question}'".strip()
    body = "\n".join(result_chunks)
    return f"{header}\n{body}"
