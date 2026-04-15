import os, json, time, tempfile, sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

file_path = r"D:\\app_Projects\\AI-Native-KG-Platform\\kg-platform-v2\\large_test.md"
with open(file_path, "rb") as f:
    files = {"file": (os.path.basename(file_path), f, "text/markdown")}
    resp = client.post("/document/upload_file", files=files)
print("Upload response:", resp.json())
extraction_id = resp.json().get("extraction_id")
if not extraction_id:
    raise SystemExit("Failed to obtain extraction_id")

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
    time.sleep(0.5)

graph = data.get("graph")
print(
    "Graph snapshot (nodes/relationships):",
    len(graph.get("nodes", [])),
    len(graph.get("relationships", [])),
)
print("Graph JSON:", json.dumps(graph, ensure_ascii=False, indent=2)[:500])
