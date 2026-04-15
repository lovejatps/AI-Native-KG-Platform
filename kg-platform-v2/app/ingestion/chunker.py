def chunk_text(text: str, size: int = 12000, overlap: int = 200):
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += max(1, size - overlap)
    return chunks
