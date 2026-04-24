import sys, importlib
sys.path.append('D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2')
engine = importlib.import_module('app.nl2sql.engine')
schema_builder = importlib.import_module('app.schema.schema_builder')
kg_id = '0b60fab0-bf76-4346-a723-dce1ab6cdba0'
schema = schema_builder.generate_schema_for_kg(kg_id)
print('entity count:', len(schema.get('entities', [])))
for e in schema.get('entities', []):
    if e.get('name') == 'grade':
        print('grade properties:', e.get('properties'))
        break
print('resolve grade 年级名称 ->', engine._resolve_column_name(schema, 'grade', '年级名称'))
