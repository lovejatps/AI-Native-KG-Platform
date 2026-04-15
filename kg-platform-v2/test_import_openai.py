try:
    import openai

    print("openai version:", getattr(openai, "__version__", "no version"))
except Exception as e:
    print("OpenAI import error:", e)
