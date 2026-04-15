import os

output_path = r"D:\app_Projects\AI-Native-KG-Platform\kg-platform-v2\large_test.md"
paragraph = """# 大段文本示例

这是一段用于测试的大段 Markdown 文本，包含一些中文字符、标点以及特殊字符 – 如破折号（\u2011）以及 emoji 😊。\n\n"""
# Repeat 10000 times (~2 MB)
with open(output_path, "w", encoding="utf-8") as f:
    for _ in range(10000):
        f.write(paragraph)
print("Created", output_path, "size:", os.path.getsize(output_path) / 1e6, "MB")
