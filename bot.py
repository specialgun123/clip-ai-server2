import os
import discord
import random

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # 중요!!!!!

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"🤖 Logged in as {client.user}")

@client.event
async def on_message(message):
    # 봇 자기 자신 무시
    if message.author.bot:
        return

    content = message.content.strip()

    # !m 호출
    if content == "!m":
        replies = [
            "Legendary call detected 😎\nUse `!m sc` to drop a clip",
            "You just summoned the meme god 👀\nTry `!m sc`",
            "I'm awake 🔥\nSend a clip with `!m sc`",
        ]
        await message.channel.send(random.choice(replies))

    # !m sc
    if content.startswith("!m sc"):
        if message.attachments:
            await message.channel.send(
                "🔥 Scuff mode ON\nProcessing your clip..."
            )
        else:
            await message.channel.send(
                "⚠️ Drop a video file with `!m sc`"
            )

client.run(TOKEN)
