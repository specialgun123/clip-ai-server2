# bot.py

import asyncio
import subprocess
import time
from enum import Enum, auto
from typing import Dict, Callable, Optional


# =========================
# 설정값
# =========================
MAX_FILE_SIZE = 25 * 1024 * 1024      # 25MB 1차 컷
MAX_DURATION = 60                     # 60초 제한
WAIT_TIMEOUT = 120                    # 입력 대기 2분
WAIT_WARNING = 60                     # 1분 경고
PROCESS_TIMEOUT = 120                 # 처리 2분
PROCESS_WARNING = 60                  # 처리 1분 경고


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
# 이벤트 정의
# =========================
class BotEvent(Enum):
    CALL = auto()
    INPUT_READY = auto()
    SUCCESS = auto()
    FAIL = auto()
    TIMEOUT = auto()
    COST_LIMIT = auto()
    RESET = auto()


# =========================
# 상태 머신
# =========================
class StateMachine:

    def __init__(self):
        self.state = BotState.IDLE
        self.last_active = time.time()

        self.pending_command: Optional[str] = None
        self.pending_video_path: Optional[str] = None
        self.pending_file_size: Optional[int] = None

        self.process_task: Optional[asyncio.Task] = None

        self.transitions: Dict[
            BotState, Dict[BotEvent, Callable[[], None]]
        ] = {
            BotState.IDLE: {
                BotEvent.CALL: self._enter_waiting,
            },
            BotState.WAITING: {
                BotEvent.INPUT_READY: self._start_processing,
                BotEvent.TIMEOUT: self._reset,
            },
            BotState.PROCESSING: {
                BotEvent.SUCCESS: self._success,
                BotEvent.FAIL: self._fail,
                BotEvent.TIMEOUT: self._processing_timeout,
                BotEvent.COST_LIMIT: self._cost_exceeded,
            },
            BotState.DONE: {
                BotEvent.RESET: self._reset,
            },
            BotState.ERROR: {
                BotEvent.RESET: self._reset,
            },
            BotState.COST_EXCEEDED: {
                BotEvent.RESET: self._reset,
            },
        }

    # =========================
    # 외부 입력 처리 (명령/영상 순서 무관)
    # =========================
    def receive_command(self, command: str):
        print(f"📩 Command received: {command}")
        self.pending_command = command
        self._handle_input()

    def receive_video(self, path: str, file_size: int):
        print(f"🎬 Video received: {path} ({file_size} bytes)")
        self.pending_video_path = path
        self.pending_file_size = file_size
        self._handle_input()

    def _handle_input(self):
        self.last_active = time.time()

        if self.state == BotState.IDLE:
            self.dispatch(BotEvent.CALL)

        if self.state == BotState.WAITING:
            if self.pending_command and self.pending_video_path:
                self.dispatch(BotEvent.INPUT_READY)

    # =========================
    # 이벤트 디스패처
    # =========================
    def dispatch(self, event: BotEvent):
        if event not in self.transitions.get(self.state, {}):
            print(f"[WARN] {event} not allowed in {self.state}")
            return

        self.transitions[self.state][event]()

    # =========================
    # 상태 전이
    # =========================
    def _enter_waiting(self):
        print("👀 Waiting for command + video")
        self.state = BotState.WAITING

    def _start_processing(self):
        print("▶ Starting validation")

        # 1️⃣ 파일 크기 컷 (비용 0원)
        if self.pending_file_size > MAX_FILE_SIZE:
            print("❌ File too large")
            self.dispatch(BotEvent.FAIL)
            return

        # 2️⃣ ffprobe 길이 체크
        duration = self._get_video_duration(self.pending_video_path)
        if duration is None or duration > MAX_DURATION:
            print("❌ Video longer than 60 seconds")
            self.dispatch(BotEvent.FAIL)
            return

        # 여기까지 통과해야 비용 발생 가능
        print("💰 Validation passed – cost may occur")

        self.state = BotState.PROCESSING
        self.process_task = asyncio.create_task(self._processing_guard())

    def _success(self):
        print("✅ Processing success")
        self._cleanup()
        self.state = BotState.DONE

    def _fail(self):
        print("❌ Processing failed")
        self._cleanup()
        self.state = BotState.ERROR

    def _processing_timeout(self):
        print("⏱ Processing timeout")
        self._cleanup()
        self.state = BotState.ERROR

    def _cost_exceeded(self):
        print("💸 Cost exceeded")
        self._cleanup()
        self.state = BotState.COST_EXCEEDED

    def _reset(self):
        print("🔄 Reset")
        self._cleanup()
        self.state = BotState.IDLE

    # =========================
    # ffprobe 길이 체크
    # =========================
    def _get_video_duration(self, path: str) -> Optional[float]:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            return float(result.stdout.strip())
        except Exception as e:
            print(f"ffprobe error: {e}")
            return None

    # =========================
    # 처리 타임아웃 가드
    # =========================
    async def _processing_guard(self):
        try:
            await asyncio.sleep(PROCESS_WARNING)
            if self.state == BotState.PROCESSING:
                print("⚠️ Processing taking longer than expected...")

            await asyncio.sleep(PROCESS_TIMEOUT - PROCESS_WARNING)
            if self.state == BotState.PROCESSING:
                self.dispatch(BotEvent.TIMEOUT)

        except asyncio.CancelledError:
            pass

    # =========================
    # 대기 타임아웃 (외부 루프에서 tick 호출)
    # =========================
    def tick(self):
        now = time.time()

        if self.state == BotState.WAITING:
            elapsed = now - self.last_active

            if WAIT_WARNING < elapsed < WAIT_TIMEOUT:
                print("⚠️ Waiting timeout soon...")

            if elapsed >= WAIT_TIMEOUT:
                print("⌛ User idle timeout")
                self.dispatch(BotEvent.TIMEOUT)

    # =========================
    # 정리
    # =========================
    def _cleanup(self):
        if self.process_task and not self.process_task.done():
            self.process_task.cancel()
        self.process_task = None

        self.pending_command = None
        self.pending_video_path = None
        self.pending_file_size = None
