# bot.py

import asyncio
import time
from enum import Enum, auto
from typing import Dict, Callable, Optional


# =========================
# State 정의
# =========================
class BotState(Enum):
    IDLE = auto()          # 아무 작업 안 함
    WAITING = auto()       # 유저 입력 대기
    PROCESSING = auto()    # 영상 처리 중
    DONE = auto()          # 완료
    ERROR = auto()         # 에러
    COST_EXCEEDED = auto() # 비용 초과


# =========================
# Event 정의
# =========================
class BotEvent(Enum):
    CALL = auto()          # 봇 호출
    INPUT = auto()         # 영상/명령 입력
    START_PROCESS = auto()
    SUCCESS = auto()
    FAIL = auto()
    TIMEOUT = auto()
    COST_LIMIT = auto()
    RESET = auto()


# =========================
# 상태 머신 본체
# =========================
class StateMachine:
    WAIT_TIMEOUT = 120          # 유저 대기 2분
    WAIT_WARNING_TIME = 60      # 1분 경고
    PROCESS_TIMEOUT = 90        # 처리 타임아웃 (초)

    def __init__(self):
        self.state = BotState.IDLE
        self.last_active = time.time()
        self.process_task: Optional[asyncio.Task] = None

        self.transitions: Dict[
            BotState, Dict[BotEvent, Callable[[], None]]
        ] = {
            BotState.IDLE: {
                BotEvent.CALL: self._enter_waiting,
            },
            BotState.WAITING: {
                BotEvent.INPUT: self._start_processing,
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
    # Event Dispatcher
    # =========================
    def dispatch(self, event: BotEvent):
        if event not in self.transitions.get(self.state, {}):
            print(f"[WARN] Event {event} not allowed in state {self.state}")
            return
        self.last_active = time.time()
        self.transitions[self.state][event]()

    # =========================
    # State Transition Logic
    # =========================
    def _enter_waiting(self):
        print("👋 Bot called, waiting for input")
        self.state = BotState.WAITING

    def _start_processing(self):
        print("▶ Start processing")
        self.state = BotState.PROCESSING
        self.process_task = asyncio.create_task(self._processing_guard())

    def _success(self):
        print("✅ Processing success")
        self._cancel_processing_task()
        self.state = BotState.DONE

    def _fail(self):
        print("❌ Processing failed")
        self._cancel_processing_task()
        self.state = BotState.ERROR

    def _processing_timeout(self):
        print("⏱ Processing timeout – force stop")
        self._cancel_processing_task()
        self.state = BotState.ERROR

    def _cost_exceeded(self):
        print("💸 Cost limit exceeded")
        self._cancel_processing_task()
        self.state = BotState.COST_EXCEEDED

    def _reset(self):
        print("🔄 Reset to idle")
        self._cancel_processing_task()
        self.state = BotState.IDLE

    # =========================
    # Guards
    # =========================
    async def _processing_guard(self):
        try:
            await asyncio.sleep(self.PROCESS_TIMEOUT)
            if self.state == BotState.PROCESSING:
                self.dispatch(BotEvent.TIMEOUT)
        except asyncio.CancelledError:
            pass

    def _cancel_processing_task(self):
        if self.process_task and not self.process_task.done():
            self.process_task.cancel()
        self.process_task = None

    # =========================
    # 외부에서 주기적으로 호출
    # =========================
    def tick(self):
        now = time.time()

        if self.state == BotState.WAITING:
            elapsed = now - self.last_active

            if elapsed > self.WAIT_WARNING_TIME and elapsed < self.WAIT_TIMEOUT:
                print("⚠️ Bot will timeout soon (1 min left)")

            if elapsed >= self.WAIT_TIMEOUT:
                print("⌛ User idle timeout")
                self.dispatch(BotEvent.TIMEOUT)
