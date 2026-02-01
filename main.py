from fastapi import FastAPI
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

@app.get("/test-ai")
def test_ai():
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input="Say hello"
        )

        return {"reply": response.output_text}

    except Exception as e:
        return {"error": str(e)}
