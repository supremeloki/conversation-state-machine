from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConversationError(Exception):
    pass


class InvalidTransitionError(ConversationError):
    def __init__(self, current: str, event: str) -> None:
        super().__init__(f"event {event!r} not allowed in state {current!r}")


class SessionState(str, Enum):
    IDLE = "idle"
    GREETED = "greeted"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    RESPONDING = "responding"
    ESCALATED = "escalated"
    CLOSED = "closed"


class ConversationEvent(str, Enum):
    USER_MESSAGE = "user_message"
    BOT_REPLY = "bot_reply"
    START_TASK = "start_task"
    TASK_DONE = "task_done"
    ESCALATE = "escalate"
    RESOLVE = "resolve"
    END = "end"


DEFAULT_TRANSITIONS: dict[tuple[SessionState, ConversationEvent], SessionState] = {
    (SessionState.IDLE, ConversationEvent.USER_MESSAGE): SessionState.GREETED,
    (SessionState.IDLE, ConversationEvent.BOT_REPLY): SessionState.GREETED,
    (SessionState.GREETED, ConversationEvent.START_TASK): SessionState.COLLECTING,
    (SessionState.GREETED, ConversationEvent.BOT_REPLY): SessionState.GREETED,
    (SessionState.COLLECTING, ConversationEvent.USER_MESSAGE): SessionState.COLLECTING,
    (SessionState.COLLECTING, ConversationEvent.START_TASK): SessionState.PROCESSING,
    (SessionState.PROCESSING, ConversationEvent.TASK_DONE): SessionState.RESPONDING,
    (SessionState.RESPONDING, ConversationEvent.BOT_REPLY): SessionState.GREETED,
    (SessionState.RESPONDING, ConversationEvent.END): SessionState.CLOSED,
    (SessionState.GREETED, ConversationEvent.END): SessionState.CLOSED,
    (SessionState.IDLE, ConversationEvent.END): SessionState.CLOSED,
}


@dataclass(frozen=True)
class Transition:
    source: SessionState
    event: ConversationEvent
    target: SessionState
    occurred_at: float
    payload: str = ""


@dataclass(frozen=True)
class TurnRecord:
    role: str
    content: str
    state_at_turn: SessionState
    recorded_at: float


class StateMachine:
    def __init__(self,
                 transitions: dict[tuple[SessionState, ConversationEvent],
                                   SessionState] | None = None,
                 hooks: dict[ConversationEvent, Callable[[Transition], None]] | None = None,
                 clock: Callable[[], float] | None = None) -> None:
        self._transitions = transitions or DEFAULT_TRANSITIONS
        self._hooks = hooks or {}
        self.state = SessionState.IDLE
        self.history: list[Transition] = []
        self._clock = clock or time.monotonic

    @property
