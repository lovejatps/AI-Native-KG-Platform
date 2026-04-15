import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.llm import LLM, openai

llm = LLM()
print("openai is", openai)
res = llm.chat('请返回 JSON {"text":"test"}')
print("chat result:", res)
