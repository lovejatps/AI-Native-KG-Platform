import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.llm import LLM, openai

print("openai:", openai)
llm = LLM()
print("model:", llm.model)
