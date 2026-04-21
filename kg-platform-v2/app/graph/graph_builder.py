from app.graph.neo4j_client import Neo4jClient

client = Neo4jClient()


def _filter_primitive_attrs(attrs: dict) -> dict:
    """Retain only primitive (int, float, str, bool) attribute values for Neo4j.
    Excludes internal metadata fields such as `_label` and `schema`."""
    excluded = {"_label", "schema"}
    return {k: v for k, v in attrs.items()
            if k not in excluded and isinstance(v, (int, float, str, bool))}



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
        # Gather raw properties excluding identifier fields
        raw_props = {k: v for k, v in e.items() if k not in ("name", "id")}
        # Flatten a nested `properties` dict if present
        if isinstance(raw_props.get("properties"), dict):
            inner = raw_props.pop("properties")
            raw_props.update(inner)
        # Keep only primitive attributes and drop internal metadata
        props = _filter_primitive_attrs(raw_props)
        # Build SET clause for properties (if any)
        set_clause = ", ".join([f"n.{k} = ${k}" for k in props]) if props else ""
        # Tag extraction-origin nodes for selective cleanup
        query = "MERGE (n:Entity {name: $name})"
        # Ensure the node carries an origin flag to distinguish from schema nodes
        set_clause = (set_clause + ", n.origin = $origin") if set_clause else "n.origin = $origin"
        query += f" SET {set_clause}"
        params = {"name": name, **props, "origin": "extraction"}
        print(f"[GraphBuilder] MERGE Entity name={name}, props={props}, origin=extraction")
        client.run(query, params)
    for r in data.get("relations", []):
        # Resolve source and target identifiers
        a = r.get("from") or r.get("source")
        b = r.get("to") or r.get("target")
        rel_type = r.get("type", "")
        # Gather raw relationship properties excluding core identifiers
        raw_rel_props = {k: v for k, v in r.items() if k not in ("from", "to", "type")}
        # Flatten nested `properties` dict if present
        if isinstance(raw_rel_props.get("properties"), dict):
            inner = raw_rel_props.pop("properties")
            raw_rel_props.update(inner)
        # Keep only primitive attributes and drop internal metadata
        rel_props = _filter_primitive_attrs(raw_rel_props)
        # Build SET clause for relationship properties
        set_clause = ", ".join([f"rel.{k} = ${k}" for k in rel_props]) if rel_props else ""
        # Use the relationship type as the Neo4j relationship label (back‑ticked to support non‑ASCII)
        query = f"""
        MATCH (a:Entity {{name: $a}})
        MATCH (b:Entity {{name: $b}})
        MERGE (a)-[rel:`{rel_type}`]->(b)
        SET rel.origin = $origin
        """
        if set_clause:
            query += f" SET {set_clause}"
        # Store additional properties (if any) on the relationship; the type is encoded in the label
        params = {"a": a, "b": b, "origin": "extraction", **rel_props}
        print(
            f"[GraphBuilder] MERGE REL source={a}, target={b}, type={rel_type}, props={rel_props}"
        )
        client.run(query, params)
