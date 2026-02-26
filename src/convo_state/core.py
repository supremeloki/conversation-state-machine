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
