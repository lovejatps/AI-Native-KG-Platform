import os
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['PYTHONIOENCODING'] = 'utf-8'
from app.core.llm import llm

messages = [
    {"role": "user", "content": "hello"},
    {"role": "assistant", "content": "Hi! How can I help?"},
    {"role": "user", "content": "今天上海天气怎么样"},
    {"role": "assistant", "content": "Sorry, I cannot provide real-time weather data."},
    {"role": "user", "content": "再问一次"},
]
print('Calling LLM...')
resp = llm.chat_vllm_direct(messages)
print('Response:', resp)
