# ------------------------------------------------------------
# run_simple_llm.py
# ------------------------------------------------------------
# 说明：
#   - 本脚本演示如何直接使用项目内部的 `llm` 单例
#   - 确保 .env 已配置 VLLM_ENDPOINT、VLLM_API_KEY、DEFAULT_LLM_MODEL
# ------------------------------------------------------------

import sys
import os

# 将项目根目录加入 sys.path（修改为实际路径）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ""))
sys.path.append(PROJECT_ROOT)

# 导入全局单例 llm
from app.core.llm import llm


def main() -> None:
    prompt = '请返回 JSON {"text":"hello"}'
    print(f"发送提示: {prompt}")
    result = llm.chat(prompt)
    print("\n--- 模型返回 ---")
    print(result)


if __name__ == "__main__":
    main()
