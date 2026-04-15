# ------------------------------------------------------------
# tests/test_vllm_direct.py
# ------------------------------------------------------------
# 直接调用 LLM.chat_vllm_direct()，验证 VLLM 端点是否可以返回真实响应。
# ------------------------------------------------------------

import os
import sys
from pathlib import Path

# 添加项目根目录到 PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# 加载 .env（同项目的 config 行为）
from dotenv import load_dotenv

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# 检查必需变量
required = ["VLLM_ENDPOINT", "VLLM_API_KEY", "DEFAULT_LLM_MODEL"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f"\n❌ 缺少环境变量: {', '.join(missing)}")
    sys.exit(1)

from app.core.llm import LLM


def main():
    llm = LLM()  # 自动读取 DEFAULT_LLM_MODEL
    print("\n=== Direct VLLM 调用测试 ===")
    print(f"模型: {llm.model}")
    prompt = (
        "请把下面的句子转换为 JSON，字段为 text 和 length。\n"
        "光学字符识别（OCR）是一种技术。"
    )
    try:
        resp = llm.chat_vllm_direct(prompt)
        print("\n[OK] VLLM 返回成功！响应前 300 字：")
        print(resp[:300])
    except Exception as e:
        print("\n[ERROR] VLLM 调用异常：")
        print(e)


if __name__ == "__main__":
    main()
