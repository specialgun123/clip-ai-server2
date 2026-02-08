# bot.py

import asyncio
from enum import Enum, auto
from typing import Dict, Callable, Optional


# =========================
# State 정의
# =========================
class BotState(Enum):
    IDLE = auto()          # 아무 작업 안 하는 상태
    WAITING = auto()       # 호출됨, 입력 대기 중
    PROCESSING = auto()    # 영상 처리 중
    DONE = auto()          # 작업 완료
    ERROR = auto()         # 에러 발생
    COST_EXCEEDED = auto() # 비용 초과


# =========================
# Event 정의
# =========================
class BotEvent(Enum):
    CALL = auto()          # 명령 or 영상으로 봇 호출
    START = auto()         # 명령+영상 충족 → 처리 시작
    SUCCESS = auto()
    FAIL = auto()
    COST_LIMIT = auto()
    RESET = auto()


# =========================
# 상태 머신 본체
# =========================
class StateMachine:
    def __init__(self, send_message: Callable[[str], None]):
        self.state = BotState.IDLE
        self.send_message = send_message

        self.idle_task: Optional[asyncio.Task] = None

        self.transitions: Dict[
            BotState, Dict[BotEvent, Callable[[], None]]
        ] = {
            BotState.IDLE: {
                BotEvent.CALL: self._enter_waiting,
            },
            BotState.WAITING: {
                BotEvent.START: self._start_processing,
                BotEvent.RESET: self._reset,
            },
            BotState.PROCESSING: {
                BotEvent.SUCCESS: self._success,
                BotEvent.FAIL: self._fail,
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
    # Event 처리
    # =========================
    def dispatch(self, event: BotEvent):
        if event not in self.transitions.get(self.state, {}):
            print(f"[WARN] Event {event} not allowed in state {self.state}")
            return

        self.transitions[self.state][event]()

    # =========================
    # State 전이 함수들
    # =========================
    def _enter_waiting(self):
        print("👀 Bot is waiting for input")
        self.state = BotState.WAITING
        self._start_idle_timer()

    def _start_processing(self):
        print("▶ Processing started")
        self._cancel_idle_timer()
        self.state = BotState.PROCESSING

    def _success(self):
        print("✅ Processing finished successfully")
        self.state = BotState.DONE

    def _fail(self):
        print("❌ Processing failed")
        self.state = BotState.ERROR

    def _cost_exceeded(self):
        print("💸 Cost limit exceeded")
        self.state = BotState.COST_EXCEEDED

    def _reset(self):
        print("🔄 Reset to idle")
        self._cancel_idle_timer()
        self.state = BotState.IDLE

    # =========================
    # Idle Timeout 로직
    # =========================
    def _start_idle_timer(self):
        self._cancel_idle_timer()
        self.idle_task = asyncio.create_task(self._idle_timeout_flow())

    def _cancel_idle_timer(self):
        if self.idle_task and not self.idle_task.done():
            self.idle_task.cancel()
        self.idle_task = None

    async def _idle_timeout_flow(self):
        try:
            # 1분 경고
            await asyncio.sleep(60)
            if self.state == BotState.WAITING:
                await self.send_message(
                    "⏳ I'm still waiting.\n"
                    "Please send a clip or command within 1 minute, "
                    "or I'll reset."
                )

            # 추가 1분 → 총 2분
            await asyncio.sleep(60)
            if self.state == BotState.WAITING:
                await self.send_message(
                    "👋 No input received. Resetting bot state."
                )
                self.dispatch(BotEvent.RESET)

        except asyncio.CancelledError:
            pass
