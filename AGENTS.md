# AGENTS.md - AI-Native KG Platform

## Project Status: Greenfield / Design Phase
This repository is currently in the **initial design phase**. It contains no implementation code, only a comprehensive Product Requirements Document (PRD) that serves as the architectural blueprint for the V2 Enterprise Knowledge Graph Platform.

## Intended Architecture (V2)
The system is designed as a "Self-Building Knowledge Graph Agent" integrating:
- **Agent Orchestration**: OpenClaw Agent Router for task delegation.
- **Knowledge Building**: LLM-driven auto-schema recognition and PDF-to-KG pipeline.
- **GraphRAG Engine**: Hybrid retrieval using Neo4j (Graph) and Milvus (Vector).
- **Storage Layer**: Neo4j for structural data and a document store for raw content.

## Proposed Tech Stack
- **Backend**: FastAPI (Python)
- **Graph DB**: Neo4j (Bolt protocol, ports 7474/7687)
- **Vector DB**: Milvus
- **AI Frameworks**: LangChain / LlamaIndex
- **LLM Integration**: GPT/Qwen/Claude via OpenAI API or VLLM
- **Document Processing**: Unstructured, Apache Tika, pdfminer.six

## Target Project Structure
When implementing, follow this verified blueprint from the PRD:
```text
kg-platform-v2/
├── app/
│   ├── main.py            # FastAPI entry point
│   ├── core/              # config.py, llm.py, logger.py
│   ├── schema/            # schema_builder.py (Auto-schema recognition)
│   ├── ingestion/         # document_loader.py, chunker.py, extractor.py
│   ├── graph/             # neo4j_client.py, graph_builder.py, queries.py
│   ├── rag/               # vector_store.py, graphrag.py
│   ├── agent/             # openclaw_agent.py, tools.py
│   └── api/               # routes.py
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Implementation Guidance
- **Core Workflow**: PDF $\rightarrow$ Text $\rightarrow$ Chunk $\rightarrow$ LLM Extraction $\rightarrow$ Neo4j Upsert.
- **GraphRAG Logic**: Use an LLM Router to decide between `Graph Query` (structural) and `Vector Search` (semantic).
- **Agent Tools**: Implement tools for `load_database`, `parse_document`, `build_schema`, `insert_graph`, and `query_graph`.

## Developer Commands (Proposed)
- **Install**: `pip install -r requirements.txt`
- **Run**: `uvicorn app.main:app --reload`
- **Infrastructure**: `docker-compose up -d` (for Neo4j/Milvus)
