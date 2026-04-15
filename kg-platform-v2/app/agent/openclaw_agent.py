from app.schema.schema_builder import build_schema
from app.ingestion.extractor import extract_kg
from app.graph.graph_builder import upsert_graph
from app.rag.graphrag import graphrag_query


class KGAgent:
    def run(self, task: str):
        if "建模" in task or "schema" in task:
            return build_schema(task)
        if "文档" in task or "PDF" in task:
            kg = extract_kg(task)
            upsert_graph(kg)
            return "OK: graph built"
        if "查询" in task:
            return graphrag_query(task)
        return "unknown task"
