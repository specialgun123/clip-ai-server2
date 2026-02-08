# bot.py

from enum import Enum, auto
from typing import Dict, Callable


# =========================
# State 정의
# =========================
class BotState(Enum):
    IDLE = auto()          # 아무 작업 안 하는 상태
    PROCESSING = auto()    # 영상 처리 중
    DONE = auto()          # 작업 완료
    ERROR = auto()         # 에러 발생
    COST_EXCEEDED = auto() # 비용 초과


# =========================
# Event 정의
# =========================
class BotEvent(Enum):
    START = auto()
    SUCCESS = auto()
    FAIL = auto()
    COST_LIMIT = auto()
    RESET = auto()


# =========================
# 상태 머신 본체
# =========================
class StateMachine:
    def __init__(self):
        self.state = BotState.IDLE
        self.transitions: Dict[
            BotState, Dict[BotEvent, Callable[[], None]]
        ] = {
            BotState.IDLE: {
                BotEvent.START: self._start_processing,
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
    def _start_processing(self):
        print("▶ Processing started")
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
        self.state = BotState.IDLE
