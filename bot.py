import os
import discord
import random
import asyncio
import subprocess
import tempfile

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# =========================
# CONFIG
# =========================

MAX_FILE_SIZE_MB = 120
MAX_DURATION_SEC = 60
WAIT_TIMEOUT_SEC = 120  # 2분 대기

# =========================
# DISCORD SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 유저 상태 저장 (채널 기준)
user_waiting = {}

# =========================
# UTILS
# =========================

def get_video_duration(file_path: str) -> float:
    """ffprobe로 영상 길이(초) 반환"""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return float(result.stdout.strip())

async def wait_timeout(channel_id):
    await asyncio.sleep(WAIT_TIMEOUT_SEC)
    if user_waiting.get(channel_id):
        del user_waiting[channel_id]
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(
                "⏰ Still waiting for your clip!\n"
                "Send a video within **60s** using `!m sc` 🙂"
            )

# =========================
# EVENTS
# =========================

@client.event
async def on_ready():
    print(f"🤖 Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    channel_id = message.channel.id

    # -------------------------
    # 영상 먼저 던진 경우
    # -------------------------
    if message.attachments and channel_id not in user_waiting:
        await message.channel.send(
            "👀 Nice clip!\n"
            "Type `!m sc` to process it into a meme."
        )
        return

    # -------------------------
    # !m 기본 호출
    # -------------------------
    if content == "!m":
        replies = [
            "Legendary summon detected 😎\nUse `!m sc` and drop a clip",
            "Meme engine online 🔥\nTry `!m sc`",
            "I'm awake 👀\nSend a video with `!m sc`",
        ]
        await message.channel.send(random.choice(replies))
        return

    # -------------------------
    # !m sc
    # -------------------------
    if content.startswith("!m sc"):
        user_waiting[channel_id] = True
        await message.channel.send(
            "🎬 **Scuff Mode ON**\n"
            "Drop a video (≤60s, ≤120MB)\n"
            "⏳ Waiting..."
        )
        asyncio.create_task(wait_timeout(channel_id))
        return

    # -------------------------
    # 영상 처리
    # -------------------------
    if channel_id in user_waiting and message.attachments:
        attachment = message.attachments[0]

        # 파일 크기 컷
        size_mb = attachment.size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            await message.channel.send(
                f"❌ File too large ({size_mb:.1f}MB)\n"
                f"Max allowed: {MAX_FILE_SIZE_MB}MB"
            )
            del user_waiting[channel_id]
            return

        # 임시 파일 저장
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            await attachment.save(tmp.name)
            temp_path = tmp.name

        # 영상 길이 체크
        try:
            duration = get_video_duration(temp_path)
        except Exception:
            await message.channel.send("❌ Failed to read video metadata.")
            os.remove(temp_path)
            del user_waiting[channel_id]
            return

        if duration > MAX_DURATION_SEC:
            await message.channel.send(
                f"⛔ Video too long ({int(duration)}s)\n"
                f"Max allowed: {MAX_DURATION_SEC}s"
            )
            os.remove(temp_path)
            del user_waiting[channel_id]
            return

        # 통과
        await message.channel.send(
            f"🔥 Clip accepted!\n"
            f"Duration: {int(duration)}s\n"
            f"Processing your meme..."
        )

        # 👉 여기서 실제 ffmpeg / AI 처리 연결
        # (지금 단계에서는 여기까지만)

        os.remove(temp_path)
        del user_waiting[channel_id]

# =========================
# RUN
# =========================

client.run(TOKEN)
