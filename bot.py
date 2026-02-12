import discord
from discord.ext import commands
import asyncio
import subprocess
import time
import uuid
from enum import Enum, auto
from typing import Dict, Optional


# =========================
# Discord 설정
# =========================
TOKEN = "YOUR_BOT_TOKEN"
PREFIX = "!"

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# =========================
# 설정값
# =========================
MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_DURATION = 30
WAIT_TIMEOUT = 120
WAIT_WARNING = 60
PROCESS_TIMEOUT = 30
PROCESS_WARNING = 15
SESSION_TTL = 600
MAX_SESSION_COST = 0.05


# =========================
# 상태 정의
# =========================
class BotState(Enum):
    IDLE = auto()
    WAITING = auto()
    PROCESSING = auto()
    DONE = auto()
    ERROR = auto()
    COST_EXCEEDED = auto()


# =========================
# 상태 머신
# =========================
class StateMachine:

    allowed_transitions = {
        BotState.IDLE: ["INPUT"],
        BotState.WAITING: ["INPUT", "TIMEOUT"],
        BotState.PROCESSING: ["SUCCESS", "FAIL", "TIMEOUT"],
        BotState.DONE: ["RESET"],
        BotState.ERROR: ["RESET"],
        BotState.COST_EXCEEDED: ["RESET"],
    }

    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.state = BotState.IDLE
        self.last_active = time.time()
        self.session_id = str(uuid.uuid4())

        self.pending_command: Optional[str] = None
        self.video_url: Optional[str] = None
        self.video_size: Optional[int] = None
        self.last_video_url: Optional[str] = None

        self.session_cost = 0.0

        self.process_task: Optional[asyncio.Task] = None

        self.wait_warning_sent = False
        self.process_warning_sent = False

    async def send(self, msg):
        await self.channel.send(msg)

    def can(self, event):
        return event in self.allowed_transitions[self.state]

    async def _handle_event(self, event):
        if not self.can(event):
            return

        if event == "SUCCESS":
            self.state = BotState.DONE
            await self.send("Boom 💥 meme deployed successfully.")
        elif event == "FAIL":
            self.state = BotState.ERROR
            await self.send("Processing failed. Try again.")
        elif event == "TIMEOUT":
            self.state = BotState.ERROR
            await self.send("Aight this taking too long ⏳ resetting.")
        elif event == "RESET":
            self._reset()

    # =========================
    # 입력
    # =========================
    async def receive_command(self, command: str):
        if not self.can("INPUT"):
            return

        command = command.strip()
        if not command:
            await self.send("Bro typed nothing 💀 try again.")
            return

        self.pending_command = command
        self.last_active = time.time()

        if self.state == BotState.IDLE:
            self.state = BotState.WAITING
            await self.send("Alright, I got the command 👀 now drop the clip.")

        await self._try_start()

    async def receive_video(self, url: str, size: int):
        if not self.can("INPUT"):
            return

        if size > MAX_FILE_SIZE:
            await self.send("That clip THICC 💾 max 25MB bro.")
            return

        if url == self.last_video_url:
            await self.send("Same clip again? We already cooked that one 🔥")
            return

        self.last_video_url = url
        self.video_url = url
        self.video_size = size
        self.last_active = time.time()

        if self.state == BotState.IDLE:
            self.state = BotState.WAITING
            await self.send("Clip received 🎥 now tell me what vibe we cooking.")

        await self._try_start()

    async def _try_start(self):
        if self.state == BotState.WAITING:
            if self.pending_command and self.video_url:
                await self._start_processing()

    # =========================
    # 처리
    # =========================
    async def _start_processing(self):
        try:
            self.state = BotState.PROCESSING
            await self.send("Analyzing your masterpiece...")

            duration = self._get_video_duration(self.video_url)
            if duration is None or duration > MAX_DURATION:
                await self._handle_event("FAIL")
                return

            # 비용 계산 예시
            self.session_cost += 0.02
            if self.session_cost > MAX_SESSION_COST:
                self.state = BotState.COST_EXCEEDED
                await self.send("Budget blown 💸 upgrade required.")
                return self._reset()

            self.process_task = asyncio.create_task(self._processing_guard())

            await asyncio.sleep(5)  # GPT + ffmpeg 자리

            if self.state == BotState.PROCESSING:
                await self._handle_event("SUCCESS")

        except Exception:
            await self._handle_event("FAIL")

        finally:
            self._reset()

    def _get_video_duration(self, url):
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    url,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            return float(result.stdout.strip())
        except:
            return None

    # =========================
    # 처리 타임아웃
    # =========================
    async def _processing_guard(self):
        try:
            await asyncio.sleep(PROCESS_WARNING)

            if self.state == BotState.PROCESSING and not self.process_warning_sent:
                await self.send("Still cooking… Gordon Ramsay mode activated 🔥")
                self.process_warning_sent = True

            await asyncio.sleep(PROCESS_TIMEOUT - PROCESS_WARNING)

            if self.state == BotState.PROCESSING:
                await self._handle_event("TIMEOUT")

        except asyncio.CancelledError:
            pass

    # =========================
    # 대기 타임아웃
    # =========================
    async def tick(self):
        now = time.time()

        if self.state == BotState.WAITING:
            elapsed = now - self.last_active

            if elapsed > WAIT_WARNING and not self.wait_warning_sent:
                await self.send("You still there? 👀")
                self.wait_warning_sent = True

            if elapsed >= WAIT_TIMEOUT:
                await self._handle_event("TIMEOUT")

    # =========================
    # 리셋
    # =========================
    def _reset(self):
        if self.process_task and not self.process_task.done():
            self.process_task.cancel()

        self.pending_command = None
        self.video_url = None
        self.video_size = None
        self.wait_warning_sent = False
        self.process_warning_sent = False
        self.state = BotState.IDLE


# =========================
# 세션 관리
# =========================
sessions: Dict[int, StateMachine] = {}


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channel_id = message.channel.id

    if channel_id not in sessions:
        sessions[channel_id] = StateMachine(message.channel)

    session = sessions[channel_id]

    # 명령 처리
    if message.content.startswith("!m"):
        await session.receive_command(message.content[2:])

    # 의미없는 호출 방어 (WAIT 상태에서 무의미한 텍스트 무시)
    elif session.state == BotState.WAITING and not message.attachments:
        return

    # 영상 처리
    if message.attachments:
        attachment = message.attachments[0]

        if not attachment.filename.lower().endswith((".mp4", ".mov", ".webm")):
            await message.channel.send("Not a video chief.")
            return

        await session.receive_video(attachment.url, attachment.size)

    await bot.process_commands(message)


# =========================
# background loop
# =========================
async def background_tick():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = time.time()
        remove_list = []

        for channel_id, session in sessions.items():
            await session.tick()
            if now - session.last_active > SESSION_TTL:
                remove_list.append(channel_id)

        for cid in remove_list:
            del sessions[cid]

        await asyncio.sleep(5)


bot.loop.create_task(background_tick())
bot.run(TOKEN)
