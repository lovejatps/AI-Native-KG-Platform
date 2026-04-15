import urllib.request, sys

url = "http://127.0.0.1:8005/extractions_page"
try:
    with urllib.request.urlopen(url) as resp:
        print("status", resp.getcode())
        data = resp.read(200).decode("utf-8", "ignore")
        print("snippet", data[:100])
except Exception as e:
    print("failed", e)
