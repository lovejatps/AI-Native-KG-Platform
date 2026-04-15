from app.core.llm import LLM

llm = LLM()
print("Model:", llm.model)
print("Calling chat...")
resp = llm.chat("Hello")
print("Response:", resp[:200])
