# Adding a Feature

The codebase uses a Feature/Handler pattern. Adding a new capability touches exactly 4 places and nothing else.

## Step 1 — Add message types

In [src/core/protocol.py](../../src/core/protocol.py), add entries to `MessageType`:

```python
class MessageType(str, Enum):
    # ... existing ...
    MY_REQUEST = "my_request"
    MY_RESPONSE = "my_response"
```

## Step 2 — Write the agent-side handler

Create `src/agent/features/my_feature.py`:

```python
from src.core.feature import FeatureHandler
from src.core.protocol import MessageType, Message
from src.core.session import Session
from src.core.transport import Connection

class MyFeature(FeatureHandler):
    handles = frozenset({MessageType.MY_REQUEST})

    async def on_connect(self, session: Session, transport: Connection) -> None:
        # Start any background tasks here
        pass

    async def handle(self, session: Session, transport: Connection, msg: Message) -> None:
        # Process incoming message, send response
        await transport.send(Message(type=MessageType.MY_RESPONSE, payload={"result": "ok"}))

    async def on_disconnect(self, session: Session) -> None:
        # Cancel background tasks here
        pass
```

## Step 3 — Write the viewer-side handler

Create `src/viewer/features/my_feature.py` — same pattern, opposite message directions.

## Step 4 — Register both handlers

In `src/agent_gui/server_worker.py`, import and register:

```python
from src.agent.features.my_feature import MyFeature

# inside _build_registry():
registry.register(MyFeature())
```

In `src/viewer_gui/network_worker.py`, same:

```python
from src.viewer.features.my_feature import MyFeature

registry.register(MyFeature())
```

That's it. The `FeatureRegistry` handles routing automatically.

---

## Binary data

If your feature needs to send large binary payloads (like screen frames or file chunks), use the binary lane instead of JSON:

```python
from src.core.protocol import BinaryMessageType, pack_binary

# Send binary frame
data = pack_binary(BinaryMessageType.FILE_CHUNK, payload_bytes)
await transport.send_binary(data)
```

Add a new `BinaryMessageType` entry in `protocol.py` and handle it in `transport.py`'s binary dispatch.

---

## GUI integration

If the feature needs UI elements (buttons, status indicators):

- **Agent side**: add widgets to `src/agent_gui/agent_window.py` or `settings_widget.py`
- **Viewer side**: add to `src/viewer_gui/main_window.py` or a new toolbar section

Signals from the asyncio world to Qt use `pyqtSignal` — see `network_worker.py` for examples (e.g. `file_status`, `fps_updated`).
