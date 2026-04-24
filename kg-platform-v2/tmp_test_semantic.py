import sys
sys.path.append('D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2')
from app.nl2sql.engine import generate_sql
schema = {
    'entities': [
        {'name':'class','properties':[{'name':'id'},{'name':'name','metadata':{'semanticName':'班级名称'}}]},
        {'name':'grade','properties':[{'name':'id'},{'name':'name','metadata':{'semanticName':'年级名称'}}]}
    ],
    'relations':[{'from':'class','to':'grade','condition':'class.grade_id = grade.id'}]
}
plan = {
    'tables':['class','grade'],
    'columns':{},
    'aggregations':['class.班级名称','grade.年级名称'],
    'filters':[]
}
print(generate_sql(plan, schema))
