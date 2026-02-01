from fastapi import FastAPI
from openai import OpenAI
import os
from fastapi import Request
import random


app = FastAPI()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

@app.get("/test-ai")
def test_ai():
    return {"reply": "AI 연결 준비중..."}


@app.post("/discord")
async def discord_webhook(req: Request):
    data = await req.json()

    # 디스코드 메시지 내용
    content = data.get("content", "")

    # 봇 무한루프 방지
    if data.get("author", {}).get("bot"):
        return {"status": "ignored"}

    # !m 호출만 반응
    if content.strip() == "!m":
        replies = [
            "레전드 크랙 명령어네요 ㅋㅋ\n`!m sc` : 스커프 밈 생성\n`!m clip` : 하이라이트 생성",
            "야 이건 그냥 부른거잖아 😂\n`!m sc` 써서 영상 던져봐",
            "memebot 대기중 😎\n!m sc 로 시작해봐"
        ]

        return {
            "content": random.choice(replies)
        }

    return {"status": "no command"}
