import sys, importlib, json
sys.path.append('D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2')
mod = importlib.import_module('app.schema.schema_builder')
print('module file:', mod.__file__)
print('available names (first 30):', [n for n in dir(mod) if not n.startswith('__')][:30])
