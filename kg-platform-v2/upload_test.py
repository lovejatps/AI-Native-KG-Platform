import requests, os

url = "http://127.0.0.1:8003/document/upload_file"
file_path = "README.md"
with open(file_path, "rb") as f:
    files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
    r = requests.post(url, files=files)
    print("Status:", r.status_code)
    print("Response:", r.text)
