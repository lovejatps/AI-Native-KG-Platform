import sys

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.config import get_settings

settings = get_settings()
print(
    "Redis host/port/password:",
    settings.REDIS_HOST,
    settings.REDIS_PORT,
    settings.REDIS_PASSWORD,
)
import redis

try:
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    r.ping()
    print("Redis connection succeeded")
except Exception as e:
    print("Redis connection failed:", e)
