import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.llm import LLM

llm = LLM()
print("model:", llm.model)
res = llm.chat('请返回 JSON {"text":"hello"}')
print("result:", res)
