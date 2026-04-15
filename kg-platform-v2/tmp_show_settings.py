import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.config import get_settings

s = get_settings()
print("VLLM_ENDPOINT:", s.VLLM_ENDPOINT)
print("VLLM_API_KEY length:", len(s.VLLM_API_KEY))
print("DEFAULT_LLM_MODEL:", s.DEFAULT_LLM_MODEL)
