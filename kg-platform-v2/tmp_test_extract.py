import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.ingestion.extractor import extract_kg

chunk = "光学字符识别（OCR）是一种技术。"
kg = extract_kg(chunk, max_retries=1)
print("Result:", kg)
