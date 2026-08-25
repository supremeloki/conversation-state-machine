# conversation-state-machine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Explicit state machine for conversational agents: typed states and events, a transition table, per-event hooks, full transition history, and session turn tracking with state snapshots.

## 🚀 Overview

Chat agents drift into impossible states because "where are we in the conversation" lives in scattered booleans. `conversation-state-machine` makes conversation flow explicit: IDLE → GREETED → COLLECTING → PROCESSING → RESPONDING, with escalation and closure as first-class transitions. Illegal event/state pairs raise `InvalidTransitionError` instead of silently corrupting the flow. The default table is a sensible support-bot shape; any custom topology is just another dict.

## ✨ Features

- **Typed states & events:** `SessionState` / `ConversationEvent` enums — no stringly-typed flow
- **Transition table:** swap in your own topology by passing a dict
- **Hooks:** fire side effects on specific events (escalation alerts, logging)
- **History:** every `Transition` recorded with timestamp + payload; replay sequences wholesale
- **allowed_events():** introspection for UI affordances ("what can happen now?")
- **ConversationSession:** turn records snapshotted with the state at that moment
- **trace_states():** generator that survives invalid events (yields current state instead of raising)
- **Terminal guard:** CLOSED sessions reject everything
- **Zero dependencies**

## 🚧 Structure

```
conversation-state-machine/
├── src/convo_state/
│   ├── __init__.py
│   └── core.py
├── tests/
│   └── test_core.py
├── README.md
└── pyproject.toml
```

## 📦 Installation

```bash
git clone https://github.com/supremeloki/conversation-state-machine.git
cd conversation-state-machine
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 📋 Requirements

- Python 3.11+
- No runtime dependencies

## 🏃 Quick Start

```python
from convo_state import (ConversationEvent, ConversationSession,
                         InvalidTransitionError)

session = ConversationSession("support-42")
session.add_user_turn("I need help with my order")
print(session.machine.state)          # greeted
print(session.machine.allowed_events())

try:
    session.machine.fire(ConversationEvent.TASK_DONE)   # illegal from greeted
except InvalidTransitionError as exc:
    print(exc)
```

## 🔧 Error Handling

```text
ConversationError
└── InvalidTransitionError    # event not allowed in current state / terminal session
```

## 🧪 Testing

```bash
pytest tests/ -v
```

## 📝 Code Quality

- Full type hints (`X | None` style), frozen transitions/turns
- Zero comments — names carry the meaning
- Happy path, invalid transitions, hooks, custom tables, and trace recovery covered

## 📄 License

MIT — see [LICENSE](LICENSE).

## 👤 Author

**Kooroush Masoumi** - [kooroushmasoumi@gmail.com](mailto:kooroushmasoumi@gmail.com)

---

⭐ Star this repo if you find it useful!
