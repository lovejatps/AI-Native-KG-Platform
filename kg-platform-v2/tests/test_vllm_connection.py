# ------------------------------------------------------------
# tests/test_vllm_connection.py
# ------------------------------------------------------------
# 这个脚本用于验证 VLLM（NVIDIA）接口是否能够通过 OpenAI SDK 正常调用。
# 只要模型返回合法的 JSON（或任意字符串），即说明连接成功。
# ------------------------------------------------------------

import os
import sys
from pathlib import Path

# 将项目根目录加入 PYTHONPATH，确保可以 import app.*
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# 加载 .env（与项目的 config 同步）
from dotenv import load_dotenv

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# 检查必须的环境变量
required = ["VLLM_ENDPOINT", "VLLM_API_KEY", "DEFAULT_LLM_MODEL"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f"\n❌ 缺少环境变量: {', '.join(missing)}")
    print("请在项目根目录的 .env 中添加以下内容（示例）:")
    print("""
VLLM_ENDPOINT=https://integrate.api.nvidia.com/v1
VLLM_API_KEY=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
DEFAULT_LLM_MODEL=qwen/qwen3.5-397b-a17b
""")
    sys.exit(1)

# 导入我们项目的 LLM 包装类
from app.core.llm import LLM


def main():
    llm = LLM()  # 会自动读取 DEFAULT_LLM_MODEL
    print("\n=== VLLM 连接测试 ===")
    print(f"模型: {llm.model}")
    print(f"VLLM_ENDPOINT: {os.getenv('VLLM_ENDPOINT')}")
    print(
        f"VLLM_API_KEY: {'*' * (len(os.getenv('VLLM_API_KEY')) - 4) + os.getenv('VLLM_API_KEY')[-4:]}"
    )
    print("-" * 40)

    # 简单的提示，要求模型返回符合 KG 提取 JSON 结构的内容
    prompt = (
        "从以下文本中抽取知识图谱要素，请严格返回 JSON，格式如下：\n"
        "{\n"
        '  "entities": [\n'
        '    {"name": "...", "type": "..."}\n'
        "  ],\n"
        '  "relations": [\n'
        '    {"from": "...", "to": "...", "type": "..."}\n'
        "  ]\n"
        "}\n"
        "下面的文本是：\n"
        "光学字符识别（OCR）是一种将图片中的文字转换为可编辑文本的技术，常用的 Python 库是 pytesseract。"
    )
    try:
        response = llm.chat(prompt)
        print("\n✅ 调用成功！原始响应（前 500 字）:")
        print("-" * 40)
        print(response[:500])
    except Exception as exc:
        print("\n❌ 调用过程中出现异常:")
        print(exc)


if __name__ == "__main__":
    main()
