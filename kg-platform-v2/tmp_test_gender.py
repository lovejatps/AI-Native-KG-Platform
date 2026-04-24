import sys, os
sys.path.append('kg-platform-v2')
from app.core.kg_store import create_kg
from app.core.models_store import create_model, publish_model
from app.nl2sql.engine import nl2sql_pipeline

kg = create_kg('testkg2', 'demo')
kg_id = kg['id']

schema = {
    "entities": [
        {"name": "class", "properties": [{"name": "id", "type": "int", "source_column": "class.id", "metadata": {"semanticName": "id"}}, {"name": "name", "type": "varchar(50)", "source_column": "class.name", "metadata": {"semanticName": "班级名称"}}, {"name": "grade_id", "type": "int", "source_column": "class.grade_id", "metadata": {"semanticName": "年级ID"}}]},
        {"name": "student", "properties": [{"name": "id", "type": "int", "source_column": "student.id", "metadata": {"semanticName": "id"}}, {"name": "name", "type": "varchar(100)", "source_column": "student.name", "metadata": {"semanticName": "姓名"}}, {"name": "class_id", "type": "int", "source_column": "student.class_id", "metadata": {"semanticName": "班级ID"}}, {"name": "gender", "type": "varchar(1)", "source_column": "student.gender", "metadata": {"semanticName": "性别"}}]},
        {"name": "grade", "properties": [{"name": "id", "type": "int", "source_column": "grade.id", "metadata": {"semanticName": "id"}}, {"name": "name", "type": "varchar(50)", "source_column": "grade.name", "metadata": {"semanticName": "年级名称"}}]}
    ],
    "relations": [{"from": "student", "to": "class", "type": "FK"}, {"from": "class", "to": "grade", "type": "FK"}]
}
model = create_model(kg_id, schema)
publish_model(kg_id, model['id'])

result = nl2sql_pipeline('1-B班有多少男同学', kg_id)
print('SQL:', result.get('sql'))
print('Result:', result.get('result'))
