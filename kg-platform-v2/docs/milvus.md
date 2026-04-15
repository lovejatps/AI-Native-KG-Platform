# Milvus 文档摘要（Python SDK）

## 目标
实现 **集合创建 → 向量插入 → 索引构建 → 加载集合 → 向量检索** 的完整流程，兼容本项目的 `VectorStore` 实现。

---

## 1️⃣ 依赖安装
```bash
pip install pymilvus
```
> 官方文档：https://milvus.io/docs/install-sdk.md

---

## 2️⃣ 连接 Milvus
```python
from pymilvus import MilvusClient

# 如使用默认本地 Milvus（docker-compose 已暴露 19530 端口）
client = MilvusClient(uri="http://localhost:19530")
```
> `MilvusClient` 构造函数支持 `uri`、`token`（云版）等参数。详细见官方文档：https://milvus.io/docs/pymilvus/v2.6.x/intro.md

---

## 3️⃣ 定义集合 Schema 并创建集合
```python
from pymilvus import (
    CollectionSchema,
    FieldSchema,
    DataType,
)

# 主键字段（整型）
id_field = FieldSchema(name="id", dtype=DataType.INT64, is_primary=True)
# 向量字段（维度 128 为示例）
vec_field = FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)

schema = CollectionSchema(fields=[id_field, vec_field], description="demo collection")

# 创建集合（若已存在会抛异常，可使用 IF NOT EXISTS 方式）
collection = client.create_collection(collection_name="demo_collection", schema=schema)
```
> 关键文档：
> - 创建集合：https://milvus.io/docs/create-collection.md
> - `CollectionSchema`、`FieldSchema` 参考：https://milvus.io/api-reference/pymilvus/v2.5.x/ORM/CollectionSchema.md

---

## 4️⃣ 向集合插入向量数据
```python
# 插入数据的格式必须与 schema 对齐
# 示例：插入 3 条记录，每条向量长度必须等于 schema 中的 dim（这里是 128）
records = {
    "id": [1, 2, 3],
    "embedding": [
        [0.1] * 128,
        [0.2] * 128,
        [0.3] * 128,
    ],
}

# 通过 Collection 对象插入（ORM 风格）
collection.insert(records)
```
> 插入 API 文档（2.5.x）： https://milvus.io/api-reference/pymilvus/v2.5.x/ORM/Collection/insert.md
> 插入 API 文档（2.6.x）： https://milvus.io/api-reference/pymilvus/v2.6.x/MilvusClient/Vector/insert.md

---

## 5️⃣ 创建向量索引（加速检索）
```python
index_params = {
    "index_type": "IVF_FLAT",   # 常用索引类型，可替换为 HNSW、IVF_PQ 等
    "metric_type": "L2",        # 距离度量（L2、IP、COSINE）
    "params": {"nlist": 1024},  # 索引参数，取决于数据规模
}

collection.create_index(field_name="embedding", index_params=index_params)
```
> 索引文档：https://milvus.io/api-reference/pymilvus/v2.5.x/ORM/Collection/create_index.md

---

## 6️⃣ 加载集合（将数据加载到查询节点内存）
```python
# 索引创建后需要加载集合才能进行搜索
collection.load()
```
> 加载集合文档：https://milvus.io/api-reference/pymilvus/v2.5.x/ORM/Collection/load.md

---

## 7️⃣ 向量检索（搜索相似向量）
```python
# 构造查询向量（同样必须是 128 维）
query_vec = [0.15] * 128

search_params = {
    "metric_type": "L2",
    "params": {"nprobe": 10},
}

results = collection.search(
    data=[query_vec],
    anns_field="embedding",
    param=search_params,
    limit=5,
    expr="",  # 可选过滤表达式，例如 "id > 0"
)

# 打印搜索结果（每条结果包含 id、距离、payload）
for hit in results[0]:
    print(f"id={hit.id}, distance={hit.distance}")
```
> 检索 API 文档（2.6.x）： https://milvus.io/api-reference/pymilvus/v2.6.x/MilvusClient/Vector/search.md

---

## 8️⃣ 常见坑点（官方文档 & 经验）
| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 插入报错 `dim mismatch` | 向量长度与集合 `dim` 不一致 | 确保 `len(vector) == schema.dim`；若维度变化，需要重新建集合。 |
| 主键冲突（`duplicate primary key`） | `id` 重复 | 主键必须唯一，使用自增或 UUID，或在插入前检查。 |
| 搜索返回空结果 | 索引未创建或未 `load()` | 完成 `create_index` 后调用 `collection.load()`；确认索引构建成功（`collection.indexes`） |
| 索引创建慢或报错 | 参数不匹配或内存不足 | 调整 `nlist`、`nprobe`；检查 Milvus 服务器资源（CPU、内存） |
| 连接超时 | Milvus 服务未启动或端口错误 | 确认 `docker-compose up -d milvus` 正常运行，端口 `19530` 可达。 |

---

## 9️⃣ 与本项目的集成点
- `app.rag.vector_store.VectorStore` 在初始化时会创建 `MilvusClient` 并在需要时自动创建集合（若不存在）。
- `VectorStore.add_text` 会先 **缓存嵌入**（Redis）→`embedder.embed` → `add_vector`（Milvus） → 标记已处理。
- `tests/integration_test.py` 已通过零向量搜索验证向量存储；如需验证索引与加载，可在测试中加入 `collection.load()` 与 `search` 断言（见下面的测试扩展示例）。

---

## 10️⃣ 示例：在集成测试中验证全文索引 & Milvus 加载
```python
# 1️⃣ 确保 Neo4j 已创建全文索引（在 Neo4jClient.__init__ 中自动调用）
neo = Neo4jClient()
neo.ensure_fulltext_index()

# 2️⃣ 插入实体后，使用全文搜索验证索引可用
entity_name = "张三"
ft_hits = neo.fulltext_search(entity_name)
assert any(hit["properties"].get("name") == entity_name for hit in ft_hits)

# 3️⃣ Milvus：插入后显式加载并搜索
store = VectorStore()
# 假设已有向量已通过 add_text 插入，这里直接搜索零向量确保 collection 已 load
hits = store.search([0.0] * store.client.dim, top_k=5)
assert len(hits) > 0  # 至少返回空向量自身或其他已插入向量
```
> 以上代码可直接粘贴进 `tests/integration_test.py`，配合 `docker-compose up -d` 运行。

---

## 11️⃣ 小结
- **创建 → 插入 → 索引 → 加载 → 检索** 是 Milvus 使用的标准流水线。
- 关注 **维度匹配、主键唯一、索引一致性**，即可避免大多数错误。
- 本项目的 `VectorStore` 已封装了这些步骤，配合 `RedisCache` 实现增量去重与向量缓存。

如需进一步的代码示例或在 CI 中加入完整测试，请告诉我！
