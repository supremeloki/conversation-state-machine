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
    def is_terminal(self) -> bool:
        return self.state is SessionState.CLOSED

    def allowed_events(self) -> tuple[ConversationEvent, ...]:
        return tuple(sorted(
            (event for (state, event) in self._transitions if state is self.state),
            key=lambda e: e.value,
        ))

    def fire(self, event: ConversationEvent, payload: str = "") -> SessionState:
        if self.is_terminal:
            raise InvalidTransitionError(self.state.value, event.value)
        key = (self.state, event)
        if key not in self._transitions:
            raise InvalidTransitionError(self.state.value, event.value)
        transition = Transition(
            source=self.state,
            event=event,
            target=self._transitions[key],
            occurred_at=self._clock(),
            payload=payload,
        )
        hook = self._hooks.get(event)
        if hook is not None:
            hook(transition)
        self.state = transition.target
        self.history.append(transition)
        return self.state

    def replay(self, events: Sequence[tuple[ConversationEvent, str]]) -> SessionState:
        for event, payload in events:
            self.fire(event, payload)
        return self.state


class ConversationSession:
    def __init__(self, session_id: str,
                 machine: StateMachine | None = None) -> None:
        self.session_id = session_id
        self.machine = machine or StateMachine()
        self.turns: list[TurnRecord] = []
        self.metadata: dict[str, Any] = {}

    def add_user_turn(self, content: str) -> TurnRecord:
        record = TurnRecord(
            role="user",
            content=content,
            state_at_turn=self.machine.state,
            recorded_at=time.time(),
        )
        self.turns.append(record)
        self.machine.fire(ConversationEvent.USER_MESSAGE, content)
        return record

    def add_bot_turn(self, content: str) -> TurnRecord:
        record = TurnRecord(
            role="assistant",
            content=content,
            state_at_turn=self.machine.state,
            recorded_at=time.time(),
        )
        self.turns.append(record)
        self.machine.fire(ConversationEvent.BOT_REPLY, content)
        return record

    @property
    def transcript(self) -> tuple[str, ...]:
        return tuple(f"{turn.role}: {turn.content}" for turn in self.turns)

    @property
    def turn_count(self) -> int:
        return len(self.turns)


def trace_states(events: Sequence[ConversationEvent]) -> Iterator[SessionState]:
    machine = StateMachine()
    for event in events:
        try:
            yield machine.fire(event)
        except InvalidTransitionError:
            yield machine.state
