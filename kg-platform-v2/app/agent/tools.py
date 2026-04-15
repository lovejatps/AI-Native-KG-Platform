from app.schema.schema_builder import build_schema as _build_schema
from app.graph.graph_builder import upsert_graph
from app.rag.graphrag import graphrag_query


def load_database():
    return {"status": "not-implemented"}


def parse_document(doc_path: str):
    return {"text": ""}


def build_schema(text: str):
    return _build_schema(text)


def insert_graph(data):
    upsert_graph(data)
    return "inserted"


def query_graph(query: str):
    return graphrag_query(query)
