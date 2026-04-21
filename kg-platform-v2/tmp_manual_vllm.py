import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.config import get_settings
import openai, time

settings = get_settings()
endpoint = settings.VLLM_ENDPOINT
key = settings.VLLM_API_KEY
print("endpoint", endpoint)
print("key length", len(key))
client = openai.OpenAI(api_key=key, base_url=endpoint.rstrip("/"), timeout=30)
prompt = '请返回 JSON {"text":"hello"}'
start = time.time()
try:
    res = client.chat.completions.create(
        model=settings.DEFAULT_LLM_MODEL, messages=[{"role": "user", "content": prompt}]
    )
    print("got response in", time.time() - start, "s")
    print(res)
except Exception as e:
    print("exception", e)
