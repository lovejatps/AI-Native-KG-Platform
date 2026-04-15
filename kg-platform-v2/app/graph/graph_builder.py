from app.graph.neo4j_client import Neo4jClient

client = Neo4jClient()


def upsert_graph(data):
    """Upsert entities and relationships into Neo4j with attribute deduplication.

    - Entities are merged on the ``name`` property (unique constraint). All provided
      attributes are set (or updated) on the node.
    - Relationships are merged on ``from`` + ``to`` + ``type``. Additional properties
      from the relationship dict are also set on the relationship.
    """
    if not data:
        return
    for e in data.get("entities", []):
        name = e.get("name") or e.get("id")
        # Collect all entity fields except the identifier itself
        props = {k: v for k, v in e.items() if k not in ("name", "id")}
        # ---- Flatten nested `properties` dict into top‑level props ----
        if isinstance(props.get("properties"), dict):
            # Merge inner dict and remove the wrapper
            inner = props.pop("properties")
            # Ensure only primitive values are kept (Neo4j does not accept nested maps)
            for pk, pv in inner.items():
                if isinstance(pv, (str, int, float, bool, list)):
                    props[pk] = pv
        # Build SET clause for properties (if any)
        set_clause = ", ".join([f"n.{k} = ${k}" for k in props]) if props else ""
        query = "MERGE (n:Entity {name: $name})"
        if set_clause:
            query += f" SET {set_clause}"
        params = {"name": name, **props}
        print(f"[GraphBuilder] MERGE Entity name={name}, props={props}")
        client.run(query, params)
    for r in data.get("relations", []):
        # Support both "from"/"to" and fallback "source"/"target" keys
        a = r.get("from") or r.get("source")
        b = r.get("to") or r.get("target")
        # Relation type string for label – use a generic REL label but store type as property
        rel_type = r.get("type", "")
        # Additional relationship properties excluding known keys
        rel_props = {k: v for k, v in r.items() if k not in ("from", "to", "type")}
        # Build SET clause for relationship properties
        set_clause = (
            ", ".join([f"rel.{k} = ${k}" for k in rel_props]) if rel_props else ""
        )
        query = """
        MATCH (a:Entity {name: $a})
        MATCH (b:Entity {name: $b})
        MERGE (a)-[rel:REL {type: $type}]->(b)
        """
        if set_clause:
            query += f" SET {set_clause}"
        params = {"a": a, "b": b, "type": rel_type, **rel_props}
        print(
            f"[GraphBuilder] MERGE REL source={a}, target={b}, type={rel_type}, props={rel_props}"
        )
        client.run(query, params)
