import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.llm import LLM, openai, _logger

print("openai type global:", type(openai))
llm = LLM()
print("model", llm.model)
# call internal request directly
client_kwargs = {
    "api_key": llm.settings.VLLM_API_KEY,
    "base_url": llm.settings.VLLM_ENDPOINT.rstrip("/"),
    "timeout": llm._default_vllm_timeout,
}
try:
    res = llm._vllm_request(
        client_kwargs=client_kwargs, prompt='请返回 JSON {"text":"test"}', max_tokens=50
    )
    print("result", res.choices[0].message.content)
except Exception as e:
    print("exception", e)
