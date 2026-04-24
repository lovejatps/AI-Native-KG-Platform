
## NL2SQL 使用指南

### 初始化业务数据库
- 业务数据库的 SQLite 表（`grade`, `class`, `student`）已在 `app/core/init_business_db.py` 中定义。
- `app/main.py` 在 FastAPI **startup** 事件里会自动调用 `init_business_db()`，确保在服务启动时表已创建并填充示例数据。

### 创建 KG 与模型
1. 使用 API（或直接在代码中）调用 `create_kg` 创建知识图谱。  
2. 为该 KG 创建模型，提供与业务表对应的 **schema**（实体 `grade`、`class`、`student`，以及 `class → grade`、`student → class` 的外键关系），状态设为 **正式**（`status: 正式`）。

### 发起 NL2SQL 查询
```python
from app.nl2sql.engine import nl2sql_pipeline

sql_result = nl2sql_pipeline('1-B班有多少学生', kg_id)
print(sql_result['sql'])      # 查看生成的 SQL
print(sql_result['result'])   # 查看查询结果
```

- 对于简单的 “X班有多少学生” 之类的自然语言，系统会使用启发式解析 `_heuristic_intent`，直接生成正确的 **JOIN** 与 **COUNT**，无需调用 LLM。  
- 若启发式无法识别，系统会回退到 LLM 解析并继续生成 SQL。

### 期望输出示例
```sql
SELECT COUNT(*) AS student_count 
FROM student s 
JOIN class c ON s.class_id = c.id 
WHERE c.name = '1-B';
```
返回结果类似 `[{ "student_count": 2 }]`。

> **注意**：`validate_sql` 在缺表情况下会返回原始 SQL，业务 DB 已经在启动时创建，实际执行将返回真实计数。