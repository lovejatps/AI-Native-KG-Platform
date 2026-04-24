import sys, importlib
sys.path.append('D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2')
engine = importlib.import_module('app.nl2sql.engine')
kg_id = '0b60fab0-bf76-4346-a723-dce1ab6cdba0'
msg = '一年级有多少学生'
out = engine.nl2sql_pipeline(msg, kg_id)
print('SQL:', out.get('sql'))
print('Result:', out.get('result'))
