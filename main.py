from fastapi import FastAPI, Request
import os
import random
import requests

app = FastAPI()

# =========================
# ENV
# =========================

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

DISCORD_API_BASE = "https://discord.com/api/v10"

HEADERS = {
    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
    "Content-Type": "application/json"
}

# =========================
# Health Check
# =========================

@app.get("/")
def root():
    return {"status": "memebot running"}

# =========================
# Discord Message Webhook
# =========================

@app.post("/discord")
async def discord_webhook(req: Request):
    data = await req.json()

    # 봇 메시지 무시 (무한루프 방지)
    if data.get("author", {}).get("bot"):
        return {"status": "ignored"}

    content = data.get("content", "").strip()
    channel_id = data.get("channel_id")
    attachments = data.get("attachments", [])

    # -----------------------
    # !m 기본 호출
    # -----------------------
    if content == "!m":
        replies = [
            "Legendary summon detected 💀\nUse `!m sc` or `!m clip`",
            "Bro just yelled my name 😭\nTry `!m sc`",
            "memebot online.\nWaiting for chaos.",
        ]
        send_message(channel_id, random.choice(replies))
        return {"status": "ok"}

    # -----------------------
    # !m sc
    # -----------------------
    if content == "!m sc":
        if not attachments:
            send_message(
                channel_id,
                "No video attached.\nDrop a clip with `!m sc` 🎥"
            )
            return {"status": "ok"}

        video_url = attachments[0]["url"]
        send_message(
            channel_id,
            f"🔥 Scuff meme mode ON\nProcessing video:\n{video_url}"
        )

        # 👉 여기 나중에 AI 처리 붙이면 됨
        return {"status": "ok"}

    # -----------------------
    # !m clip
    # -----------------------
    if content == "!m clip":
        if not attachments:
            send_message(
                channel_id,
                "Attach a video to extract highlights 🎬"
            )
            return {"status": "ok"}

        video_url = attachments[0]["url"]
        send_message(
            channel_id,
            f"🎬 Highlight mode ON\nAnalyzing:\n{video_url}"
        )

        return {"status": "ok"}

    return {"status": "ignored"}

# =========================
# Discord Send Message
# =========================

def send_message(channel_id: str, content: str):
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
    payload = {"content": content}
    requests.post(url, headers=HEADERS, json=payload)
