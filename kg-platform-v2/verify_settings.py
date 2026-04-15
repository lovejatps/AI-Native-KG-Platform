"""验证 .env 配置是否被正确读取"""

import sys
import os
from pathlib import Path

# 设置 PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 打印 .env 文件路径
env_file = project_root.parent / ".env"
print(f"项目根目录: {project_root}")
print(f".env 文件路径: {env_file}")
print(f".env 文件存在: {env_file.exists()}")

# 尝试切换到项目根目录并加载配置
os.chdir(project_root)
print(f"\n当前工作目录: {os.getcwd()}")

from app.core.config import get_settings

settings = get_settings()

print("\n=== Settings 配置 ===")
print(f"NEO4J_URI: {settings.NEO4J_URI}")
print(f"NEO4J_USER: {settings.NEO4J_USER}")
print(f"NEO4J_PASSWORD: {settings.NEO4J_PASSWORD}")
print(f"MILVUS_HOST: {settings.MILVUS_HOST}")
print(f"MILVUS_PORT: {settings.MILVUS_PORT}")
print(f"REDIS_HOST: {settings.REDIS_HOST}")
print(f"REDIS_PORT: {settings.REDIS_PORT}")
print(f"REDIS_PASSWORD: {settings.REDIS_PASSWORD}")
print(f"VLLM_ENDPOINT: {settings.VLLM_ENDPOINT}")
print(
    f"VLLM_API_KEY: {settings.VLLM_API_KEY[:20]}..."
    if settings.VLLM_API_KEY
    else "VLLM_API_KEY: (empty)"
)
print(f"VLLM_EMBED_MODEL: {settings.VLLM_EMBED_MODEL}")
print(f"DEFAULT_LLM_MODEL: {settings.DEFAULT_LLM_MODEL}")
print(f"ENV: {settings.ENV}")
print("\n=== 验证完成 ===")
