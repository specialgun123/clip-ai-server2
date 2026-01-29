from fastapi import FastAPI
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/test-ai")
def test_ai():
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "너는 친절한 테스트봇이야"},
            {"role": "user", "content": "서버 연결 테스트"}
        ]
    )

    return {
        "reply": response.choices[0].message.content
    }
