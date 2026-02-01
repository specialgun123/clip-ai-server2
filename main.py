from fastapi import FastAPI, Request, Header
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import json
import os
import random
from openai import OpenAI

app = FastAPI()

# =========================
# ENV
# =========================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# Test Endpoint
# =========================

@app.get("/")
def root():
    return {"status": "memebot running"}

@app.get("/test-ai")
def test_ai():
    return {"reply": "AI 연결 준비 완료 😎"}

# =========================
# Discord Interaction Endpoint
# =========================

@app.post("/interactions")
async def interactions(
    request: Request,
    x_signature_ed25519: str = Header(None),
    x_signature_timestamp: str = Header(None),
):

    # ---------- Security Check ----------

    if not DISCORD_PUBLIC_KEY:
        return {"error": "missing discord public key"}

    body = await request.body()

    verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))

    try:
        verify_key.verify(
            x_signature_timestamp.encode() + body,
            bytes.fromhex(x_signature_ed25519),
        )
    except BadSignatureError:
        return {"error": "invalid request signature"}

    data = json.loads(body)

    # ---------- Discord Ping ----------

    if data["type"] == 1:
        return {"type": 1}

    # ---------- Slash Command ----------

    if data["type"] == 2:
        command_name = data["data"]["name"]

        # /m command
        if command_name == "m":

            options = data["data"].get("options")

            # ---------------------------
            # /m only (no option)
            # ---------------------------

            if not options:
                replies = [
                    "레전드 크랙 호출이네 ㅋㅋ\n👉 `/m sc` : 스커프 밈 생성\n👉 `/m clip` : 하이라이트 추출",
                    "야 그냥 부른거잖아 😂\n`/m sc` 로 영상 던져봐",
                    "memebot 대기중 😎\n/m sc 로 시작 ㄱㄱ",
                ]

                return {
                    "type": 4,
                    "data": {"content": random.choice(replies)},
                }

            # ---------------------------
            # option parsing
            # ---------------------------

            sub_command = options[0]["name"]

            # ---------------------------
            # /m sc
            # ---------------------------

            if sub_command == "sc":
                return {
                    "type": 4,
                    "data": {
                        "content": "🔥 스커프 모드 ON\n영상 올려주면 바로 크랙 밈 만들어줄게"
                    },
                }

            # ---------------------------
            # /m clip
            # ---------------------------

            if sub_command == "clip":
                return {
                    "type": 4,
                    "data": {
                        "content": "🎬 하이라이트 모드 ON\n영상 업로드 ㄱㄱ"
                    },
                }

        # Unknown slash command fallback
        return {
            "type": 4,
            "data": {"content": "뭔 명령인지 모르겠는데요 🤔"},
        }

    return {"status": "ignored"}
