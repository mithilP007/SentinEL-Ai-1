import os
try:
    print("Importing langchain_google_genai...")
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("Import Success.")
except Exception as e:
    print(f"Import Failed: {e}")
    import traceback
    traceback.print_exc()

api_key = "AIzaSyCfC_V0veRb5WC_WwVmaxgyQZ-uTWinCwc"

if ChatGoogleGenerativeAI:
    try:
        print("Initializing LLM...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=api_key
        )
        print("Invoking LLM...")
        res = llm.invoke("Hello, are you there?")
        print(f"Response: {res.content}")
        print("SUCCESS")
    except Exception as e:
        print(f"Invocation Failed: {e}")
