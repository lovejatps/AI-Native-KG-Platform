import sys, os
sys.path.append('kg-platform-v2')
from app.nl2sql.engine import _foreign_key_column

schema = {
    "entities": [
        {"name": "class", "properties": [{"name": "id", "source_column": "class.id"}, {"name": "name", "source_column": "class.name"}]},
        {"name": "student", "properties": [{"name": "id", "source_column": "student.id"}, {"name": "class_id", "source_column": "student.class_id"}]}
    ],
    "relations": [{"from": "student", "to": "class", "type": "FK"}]
}
print('fk student->class:', _foreign_key_column(schema, 'student', 'class'))
print('fk class->student:', _foreign_key_column(schema, 'class', 'student'))
