# Neo4j 文档摘要

## 全文索引 (Full‑Text Index)

### 创建索引
```cypher
-- 节点全文索引
CREATE FULLTEXT INDEX entity_name_index
FOR (n:Entity) ON EACH [n.name]
OPTIONS {indexConfig: {`fulltext.analyzer`: 'english', `fulltext.eventually_consistent`: true}}

-- 关系全文索引（如有需要）
CREATE FULLTEXT INDEX rel_idx FOR ()-[r:REL_TYPE]-() ON EACH [r.prop]
```

### 查询索引
```cypher
CALL db.index.fulltext.queryNodes('entity_name_index', "search term") YIELD node, score
RETURN node.name AS name, score
```

**关键点**
- 支持多个标签 `(:LabelA|LabelB)`，使用 `|` 分隔。
- 可选分析器：`standard-no-stop-words`, `english` 等。
- `eventually_consistent: true` 提高写入性能。
- 查询语法基于 Lucene，支持通配符 `*`、模糊 `~`、布尔运算符。

## 可变长度路径查询 (Variable‑Length Path)

### 基本语法
```cypher
-- 1 到 5 跳数
(a)-[:KNOWS*1..5]->(b)

-- 上限 5，默认下限 1
(a)-[:KNOWS*..5]->(b)

-- 至少 2 跳
(a)-[:KNOWS*2..]->(b)

-- 正好 3 跳
(a)-[:KNOWS*3]->(b)

-- 任意长度（谨慎使用）
(a)-[*]->(b)
```

### 多种关系类型
```cypher
()-[r:R|S|T*5]->()
```

### 带属性过滤的路径
```cypher
(:A)-[* {p: $param}]->(:B)
```

### Neo4j 5+ 中的 `WHERE` 过滤示例
```cypher
MATCH p = (a:Person)-[r:KNOWS WHERE r.since < 2011]->{1,4}(:Person)
RETURN p
```

**最佳实践**
- **始终设置上限**，防止遍历无界限导致性能灾难。
- 使用 `LIMIT`、`WHERE` 或属性过滤缩小结果范围。
- 通过 `nodes(p)`、`relationships(p)` 提取路径元素。
- 对于复杂查询，可结合 `CALL db.index.fulltext.queryNodes` 先做节点过滤，再执行可变长度遍历。

---

上述内容来源于 Neo4j 官方文档（全文索引、可变长度路径章节）以及项目实现代码 (`Neo4jClient.ensure_fulltext_index`、`Neo4jClient.variable_path_query`)。