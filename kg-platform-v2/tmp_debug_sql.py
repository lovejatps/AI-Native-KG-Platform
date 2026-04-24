import sys, os, json
sys.path.append('kg-platform-v2')
from app.nl2sql.engine import _heuristic_intent, generate_sql, _foreign_key_column

schema = {
    "entities": [
        {"name": "class", "properties": [{"name": "id", "source_column": "class.id", "metadata": {"semanticName": "id"}}, {"name": "name", "source_column": "class.name", "metadata": {"semanticName": "班级名称"}}]},
        {"name": "student", "properties": [{"name": "id", "source_column": "student.id", "metadata": {"semanticName": "id"}}, {"name": "class_id", "source_column": "student.class_id", "metadata": {"semanticName": "班级ID"}}, {"name": "gender", "source_column": "student.gender", "metadata": {"semanticName": "性别"}}]}
    ],
    "relations": [{"from": "student", "to": "class", "type": "FK"}]
}
msg = '1-B班有多少男同学'
intent = _heuristic_intent(msg, schema)
print('intent', intent)
sql = generate_sql(intent, schema)
print('SQL', sql)
