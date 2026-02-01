from fastapi import FastAPI
from fastapi import Request, Header
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import json
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
    if content.strip() == "/m":
        replies = [
            "레전드 크랙 명령어네요 ㅋㅋ\n`!m sc` : 스커프 밈 생성\n`!m clip` : 하이라이트 생성",
            "야 이건 그냥 부른거잖아 😂\n`!m sc` 써서 영상 던져봐",
            "memebot 대기중 😎\n!m sc 로 시작해봐"
        ]

        return {
            "content": random.choice(replies)
        }

    return {"status": "no command"}

DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")


@app.post("/interactions")
async def interactions(request: Request,
                       x_signature_ed25519: str = Header(None),
                       x_signature_timestamp: str = Header(None)):

    body = await request.body()

    verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))

    try:
        verify_key.verify(
            x_signature_timestamp.encode() + body,
            bytes.fromhex(x_signature_ed25519)
        )
    except BadSignatureError:
        return {"error": "invalid request signature"}

    data = json.loads(body)

    # Discord ping test
    if data["type"] == 1:
        return {"type": 1}

    # Slash command
    if data["type"] == 2:
        name = data["data"]["name"]

        if name == "m":
            return {
                "type": 4,
                "data": {
                    "content": "😎 memebot 준비 완료!\n`/m sc` : 크랙 밈 생성\n`/m clip` : 하이라이트 추출"
                }
            }

    return {"type": 4, "data": {"content": "unknown command"}}
