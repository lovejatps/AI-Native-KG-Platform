
新增需求：

## 语义词典（规则 + 同义词）

### **架构：**

```
       ┌────────────┐
       │    NL                  │
       └─────┬──────┘
                   ↓
    ┌────────────────┐
    │   🧠 LLM层                    │
    │ 意图 + 实体解析                │
    └─────┬──────────┘
                ↓
 ┌───────────────────┐
 │  语义解析引擎                        │
 │（词典+规则+向量）                    │
 └─────┬────────────┘
             ↓
 ┌──────────────────┐
 │  Schema & JOIN层                   │
 └─────┬────────────┘
             ↓
 ┌──────────────────┐
 │   SQL生成引擎                      │
 └─────┬────────────┘
             ↓
     数据库（SQL执行）
```

整体架构虽然给出了向量，但当前不实现，后期再完善

首先在Sqlite 创建一个wankaNl2SQl库，库中有两个表：字段语义表（field_dictionary）与值映射表（value_dictionary）

#### 字段语义表（字段识别）

CREATE TABLE field_dictionary (  
id INT AUTO_INCREMENT PRIMARY KEY,  
library_name VARCHAR(50),  
table_name VARCHAR(50),  
column_name VARCHAR(50),  
synonyms TEXT, -- JSON数组  
description VARCHAR(255)  
);

**示例数据**：  
INSERT INTO field_dictionary (table_name, column_name, synonyms)
VALUES
('SchoolA','student', 'gender', '["性别","男女","男生","女生"]'),
('SchoolA','grade', 'name', '["年级","几年级","高一","高二"]'),
('SchoolA','class', 'name', '["班级","几班","1班","2班"]');

#### 值映射表

CREATE TABLE value_dictionary (  
id INT AUTO_INCREMENT PRIMARY KEY,  
library_name VARCHAR(50),  
table_name VARCHAR(50),  
column_name VARCHAR(50),  
display_value VARCHAR(50),  
actual_value VARCHAR(50),  
synonyms TEXT -- JSON数组  
);

**示例数据**  
INSERT INTO value_dictionary (table_name, column_name, display_value, actual_value, synonyms)  
VALUES  
('SchoolA','student', 'gender', '男', 'M', '\["男","男生","男性","male"\]'),  
('SchoolA','student', 'gender', '女', 'F', '\["女","女生","女性","female"\]'),  
('SchoolA','grade', 'name', '一年级', '一年级', '\["一年级","高一","1年级"\]');

#### 加载词典（启动时）

```python
import json
import sqlite3

conn = sqlite3.connect("dict.db")
cursor = conn.cursor()

def load_dictionaries():
    field_dict = []
    value_dict = []

    for row in cursor.execute("SELECT table_name, column_name, synonyms FROM field_dictionary"):
        field_dict.append({
            "table": row[0],
            "column": row[1],
            "synonyms": json.loads(row[2])
        })

    for row in cursor.execute("SELECT table_name, column_name, display_value, actual_value, synonyms FROM value_dictionary"):
        value_dict.append({
            "table": row[0],
            "column": row[1],
            "display": row[2],
            "actual": row[3],
            "synonyms": json.loads(row[4])
        })

    return field_dict, value_dict

FIELD_DICT, VALUE_DICT = load_dictionaries()
```

&nbsp;

#### 字段语义字典 页面原型

1、在现有页签“数据源管理”后面增加“语义词典” 如：  
知识图谱列表 | Chat | 数据源管理 | **语义词典**  
**字段语义字典**|值映射字典

【表名】输入框 【字段名】输入框 【描述】模糊搜索框  
\[ 重置 \] \[ 查询 \] \[ 新增字段字典 \]

**表格**

| ID  | 所属数据库 | 所属表名 | 字段名称 | 字段同义词 | 字段描述 | 操作  |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1   | SchoolA | student | gender | 男，性别，性别类型 | 学生性别字段 | 编辑 / 删除 |
| 2   | SchoolB | student | name | 姓名，名字，全名 | 学生姓名 | 编辑 / 删除 |

**底部**  
分页：上一页 / 页码 / 下一页 / 每页条数选择

**新增弹窗**

```plaintext
系统（必选）：[ 下拉框 ]
数据库（必选）[ 下拉框 ]
表名（必填）：[下拉框 ]
字段名（必填）：[ 下接框]
同义词（JSON数组）：[ 文本域 ]  提示：格式 ["关键词1","关键词2"]
字段描述：[ 文本输入框 ]
[ 取消 ]        [ 确定保存 ]
```

系统、数据库、表名、字段名 参考实体属性编辑中原始字段 ，数据也是来源于数据源管理下的数据；

#### 值映射字典 页面原型

知识图谱列表 | Chat | 数据源管理 | **语义词典**  
字段语义字典|**值映射字典**  
【表名】输入框 【字段名】输入框  
【显示值】输入框 【实际存储值】输入框  
\[ 重置 \] \[ 查询 \] \[ 新增值映射配置 \]

| ID  | 所属数据库 | 所属表名 | 关联字段 | 前端显示值 | 数据库实际值 | 值同义词 | 操作  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1   | SchoolA | student | gender | 男   | M   | 男生，男性 | 编辑 / 删除 |
| 2   | SchoolB | student | gender | 女   | F   | 女生，女性 | 编辑 / 删除 |

**新增值映射 弹窗**  
标题：新增字段值映射

```plaintext
系统（必选）：[ 下拉框 ]
数据库（必选）[ 下拉框 ]
表名（必填）：[下拉框 ]
字段名（必填）：[ 下接框]
展示文案（必填）：[输入框]
实际存储值（必填）：[输入框]
值同义词（JSON数组）：[文本域] 示例：["一年级","1年级","高一"]

[ 取消 ]   [ 提交保存 ]
```

系统、数据库、表名、字段名 参考实体属性编辑中原始字段 ，数据也是来源于数据源管理下的数据；

#### 公共交互规则（统一规范）

**1、表单校验**  
表名、字段名、展示值、实际值：非空校验  
synonyms 自动校验 JSON 数组格式，格式错误给出提示  
**2、唯一约束提示**  
字段字典：同表 + 同字段 重复弹窗提示  
值映射：同表 + 同字段 + 同实际值 重复拦截  
**3、统一操作反馈**  
新增 / 编辑 / 删除 成功：顶部轻提示  
异常：弹窗错误文案