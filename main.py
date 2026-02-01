from fastapi import FastAPI
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

@app.get("/test-ai")
def test_ai():
    return {"reply": "AI 연결 준비중..."}
