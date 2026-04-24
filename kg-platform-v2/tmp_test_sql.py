import sys
sys.path.append('D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2')
from app.nl2sql.engine import generate_sql
schema = {
    'entities': [
        {'name': 'student', 'properties': [{'name': 'id'}, {'name': 'class_id'}, {'name': 'gender'}]},
        {'name': 'class', 'properties': [{'name': 'id'}, {'name': 'name'}]}
    ],
    'relations': [
        {'from': 'student', 'to': 'class', 'condition': 'student.class_id = class.id'}
    ]
}
plan = {
    'tables': ['student', 'class'],
    'columns': {},
    'aggregations': ['COUNT(*) AS student_count'],
    'filters': ["class.name = '1-C'", "student.gender = 'M'"]
}
print(generate_sql(plan, schema))
