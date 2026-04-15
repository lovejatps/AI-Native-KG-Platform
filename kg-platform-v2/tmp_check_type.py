import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.llm import openai, LLM

print("openai type:", type(openai))
print("has OpenAI attribute?", hasattr(openai, "OpenAI"))
