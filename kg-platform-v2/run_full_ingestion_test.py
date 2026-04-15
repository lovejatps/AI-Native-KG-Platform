# -*- coding: utf-8 -*-
"""
完整的 API 流程测试脚本（无需手动启动 uvicorn）
1. 使用 FastAPI TestClient 启动应用（相当于在内存中启动服务器）
2. 使用本地 Markdown 文件 `C:/Users/huxiaoning/Downloads/qz_test.md` 进行上传
3. 调用 `/document/upload_file` 上传文件，获取 `extraction_id`
4. 轮询 `/extraction_status/{extraction_id}` 直至完成
5. 获取 graph，保存为 `graph.json`
6. 演示查询单个实体 `/entity/{name}`
"""

import os, json, time, tempfile, sys
from fastapi.testclient import TestClient

# Ensure console output is UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 项目根目录的模块路径已在 PYTHONPATH 中（确保能够 import app.main）
from app.main import app

client = TestClient(app)

# ---------- 使用真实 Markdown 文件 ----------
file_path = r"C:/Users/huxiaoning/Downloads/qz_test.md"

# ---------- 上传文件获取 extraction_id ----------
with open(file_path, "rb") as f:
    files = {"file": (os.path.basename(file_path), f, "text/markdown")}
    resp = client.post("/document/upload_file", files=files)
print("Upload response:", resp.json())
extraction_id = resp.json().get("extraction_id")
if not extraction_id:
    raise SystemExit("Failed to obtain extraction_id")

# ---------- 轮询状态直至完成 ----------
status_url = f"/extraction_status/{extraction_id}"
while True:
    r = client.get(status_url)
    data = r.json()
    print("Polling status:", data)
    if data.get("status") == "completed":
        print("✅ Extraction completed")
        break
    if data.get("status") == "failed":
        raise SystemExit(f"Extraction failed: {data.get('message')}")
    time.sleep(1)

# ---------- 取得 graph（已在 polling 响应中） ----------
graph = data.get("graph")
print(
    "Graph snapshot (nodes count / rel count):",
    len(graph.get("nodes", [])),
    len(graph.get("relationships", [])),
)

# ---------- 保存 graph 为本地 JSON 文件 ----------
out_path = os.path.join(tempfile.gettempdir(), "graph.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(graph, f, ensure_ascii=False, indent=2)
print(f"Graph 已保存至 {out_path}")

# ---------- 查询单个实体（示例） ----------
if graph.get("nodes"):
    first_entity = graph["nodes"][0]["id"]
    entity_resp = client.get(f"/entity/{first_entity}")
    print(f"Entity '{first_entity}' 信息:", entity_resp.json())
else:
    print("Graph 中无实体，跳过实体查询示例")

"""
运行此脚本即可完成整套上传‑抽取‑获取‑持久化‑查询流程，无需手动启动 HTTP 服务。
"""
