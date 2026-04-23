import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from convo_state import (
    ConversationEvent,
    ConversationSession,
    InvalidTransitionError,
    SessionState,
    StateMachine,
    trace_states,
)


def test_initial_state_is_idle():
    assert StateMachine().state is SessionState.IDLE


def test_happy_path_transitions():
    machine = StateMachine()
    assert machine.fire(ConversationEvent.USER_MESSAGE) is SessionState.GREETED
    assert machine.fire(ConversationEvent.START_TASK) is SessionState.COLLECTING
    assert machine.fire(ConversationEvent.START_TASK) is SessionState.PROCESSING
    assert machine.fire(ConversationEvent.TASK_DONE) is SessionState.RESPONDING
    assert machine.fire(ConversationEvent.BOT_REPLY) is SessionState.GREETED


def test_invalid_transition_raises():
    machine = StateMachine()
    with pytest.raises(InvalidTransitionError):
        machine.fire(ConversationEvent.TASK_DONE)


def test_closed_session_rejects_everything():
    machine = StateMachine()
    machine.fire(ConversationEvent.END)
    assert machine.is_terminal
    with pytest.raises(InvalidTransitionError):
        machine.fire(ConversationEvent.USER_MESSAGE)


def test_allowed_events_reflect_state():
    machine = StateMachine()
    idle_events = machine.allowed_events()
    assert ConversationEvent.USER_MESSAGE in idle_events
    machine.fire(ConversationEvent.END)
    assert machine.allowed_events() == ()


def test_history_records_full_trace():
    clock_values = iter([1.0, 2.0, 3.0])
    machine = StateMachine(clock=lambda: next(clock_values))
    machine.fire(ConversationEvent.USER_MESSAGE, "hi")
    machine.fire(ConversationEvent.START_TASK)
    assert len(machine.history) == 2
    assert machine.history[0].payload == "hi"
    assert machine.history[0].occurred_at < machine.history[1].occurred_at


def test_hooks_fire_on_event():
    fired: list[str] = []
    hooks = {ConversationEvent.ESCALATE: lambda t: fired.append(t.payload)}
    machine = StateMachine(hooks=hooks)
    transitions = dict(machine._transitions)
    transitions[(SessionState.GREETED, ConversationEvent.ESCALATE)] = \
        SessionState.ESCALATED
    custom = StateMachine(transitions=transitions, hooks=hooks)
    custom.fire(ConversationEvent.USER_MESSAGE)
    custom.fire(ConversationEvent.ESCALATE, "angry user")
    assert fired == ["angry user"]
    assert custom.state is SessionState.ESCALATED


def test_custom_transitions_table():
    table = {
        (SessionState.IDLE, ConversationEvent.ESCALATE): SessionState.ESCALATED,
        (SessionState.IDLE, ConversationEvent.RESOLVE): SessionState.CLOSED,
    }
    machine = StateMachine(transitions=table)
    assert machine.allowed_events() == (ConversationEvent.ESCALATE,
                                        ConversationEvent.RESOLVE)


def test_replay_sequence():
    machine = StateMachine()
    final = machine.replay([
        (ConversationEvent.USER_MESSAGE, "hello"),
        (ConversationEvent.START_TASK, ""),
        (ConversationEvent.START_TASK, "data"),
        (ConversationEvent.TASK_DONE, ""),
        (ConversationEvent.BOT_REPLY, "here you go"),
    ])
    assert final is SessionState.GREETED


def test_session_records_turns():
    session = ConversationSession("s-1")
    session.add_user_turn("What's the weather?")
    session.add_bot_turn("Sunny.")
    assert session.turn_count == 2
    assert session.transcript[0].startswith("user:")
    roles = [turn.role for turn in session.turns]
    assert roles == ["user", "assistant"]


def test_session_states_snapshotted_per_turn():
