import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.ingestion.extractor import extract_kg

text = "青竹峰上，小弟子阿禾终日打坐练气，却总因心浮气躁无法凝聚灵力。"
kg = extract_kg(text, max_retries=2)
print("KG result:", kg)
