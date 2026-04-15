# AI Native KG Platform

## 项目概述
本仓库实现 **AI‑Native 知识图谱平台（V2）**，核心功能包括：
- **文档处理**：从 PDF、TXT 等文件抽取原始文本。
- **LLM 抽取**：利用 LLM 自动识别实体、属性与关系，生成结构化的 KG 数据。
- **图谱存储**：实体与关系写入 Neo4j（结构化）与 Milvus（向量化）实现 GraphRAG 混合检索。
- **前端交互**：提供搜索、上传、实体详情、图谱可视化（Cytoscape.js）等 UI。
- **可扩展**：采用 FastAPI、LangChain/LlamaIndex、OpenAI/VLLM、Anthropic 等，可灵活替换底层模型与向量库。

> 项目仍处于 **绿色设计阶段**，大多数实现已完成，正在持续完善测试、文档与 UI 细节。

## 项目结构
```
kg-platform-v2/
├─ app/               # FastAPI 应用代码
│  ├─ api/           # 路由 & 端点实现
│  ├─ core/          # 配置、LLM 抽象、日志、存储等通用模块
│  ├─ graph/         # Neo4j 客户端、图构建、查询工具
│  ├─ ingestion/     # 文档加载、分块、抽取管线
│  ├─ rag/           # VectorStore (Milvus) & GraphRAG 融合检索
│  └─ schema/        # 自动 schema 生成与缓存
├─ docs/              # 设计文档、Neo4j / Milvus 使用指南
├─ docker-compose.yml # 启动 Neo4j、Milvus、Redis 等依赖
├─ requirements.txt   # Python 依赖
└─ tests/             # 单元与集成测试
```

## 关键技术栈
- **后端**：FastAPI（Python 3.11）
- **图数据库**：Neo4j（Bolt 协议）
- **向量数据库**：Milvus
- **大模型**：OpenAI / VLLM / Anthropic（统一封装在 `app/core/llm.py`）
- **文档解析**：`unstructured`、`apache-tika`、`pdfminer.six`
- **检索框架**：LangChain / LlamaIndex
- **前端**：Vanilla HTML/JS + **Cytoscape.js**（图谱交互式渲染）

## 快速开始
### 1️⃣ 启动依赖服务
```bash
docker-compose up -d   # 启动 Neo4j、Milvus、Redis
```
### 2️⃣ 安装 Python 依赖
```bash
pip install -r requirements.txt
```
### 3️⃣ 运行 API（开发模式）
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```
### 4️⃣ 访问前端页面
- 搜索首页: `http://localhost:8005/ui`
- 上传文档: `http://localhost:8005/upload`
- 实体详情: `http://localhost:8005/entity_page?name=<实体名>`
- 图谱查看: `http://localhost:8005/graph_view?eid=<extraction_id>`（使用 Cytoscape.js 渲染）

## 测试套件
```bash
pytest -q tests/
```
新增的测试覆盖：
- **GET `/entity/{name}` 404**（`tests/test_entity_endpoint.py`）
- **Neo4j variable_path_query** 多跳查询（`tests/test_neo4j_variable_path.py`）
- 现有核心功能（schema、向量、图 upsert）保持不变。

## 文档资源
- **Neo4j**：`docs/neo4j.md` 包含全文索引、可变长度路径的创建与最佳实践。
- **Milvus**：`docs/milvus.md` 说明集合、向量插入、索引与搜索的完整步骤。

## 进一步阅读 & 贡献指南
- **Neo4j 官方文档**： https://neo4j.com/docs/cypher-manual/current/
- **Milvus 官方文档**： https://milvus.io/docs/python-sdk-v2.5.x.md
- **贡献**：请遵循 PEP8、使用 `black` 格式化代码、提交前确保所有 `pytest` 通过。

---

*本 README 将随项目迭代持续更新，如有新功能或架构变更请同步至此文件。*
