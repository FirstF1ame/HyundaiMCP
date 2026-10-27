import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import NavigationSnapshot


@dataclass
class Pending:
    future: asyncio.Future
    delivered: bool = False


class Broker:
    """In-memory single-vehicle broker. One server worker only; no persistent location logs."""

    def __init__(self, timeout: float):
        self.timeout = timeout
        self.pending: dict[str, Pending] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=16)
        self.last_poll = 0.0

    async def query(self) -> dict:
        if time.monotonic() - self.last_poll > 20:
            return {"status": "bridge_offline", "source": "pleos_bridge"}
        if len(self.pending) >= 16 or self.queue.full():
            return {"status": "busy", "source": "pleos_bridge"}
        command_id = str(uuid.uuid4())
        item = Pending(asyncio.get_running_loop().create_future())
        self.pending[command_id] = item
        self.queue.put_nowait(command_id)
        try:
            snapshot = await asyncio.wait_for(item.future, timeout=self.timeout)
            age = (datetime.now(timezone.utc) - snapshot.observed_at).total_seconds()
            if age > 30 or age < -5:
                return {"status": "stale_data", "source": "pleos_bridge"}
            return snapshot.model_dump(mode="json")
        except TimeoutError:
            return {"status": "timeout", "source": "pleos_bridge"}
        finally:
            self.pending.pop(command_id, None)

    async def next_command(self) -> dict | None:
        self.last_poll = time.monotonic()
        deadline = time.monotonic() + 10
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                command_id = await asyncio.wait_for(self.queue.get(), remaining)
            except TimeoutError:
                return None
            item = self.pending.get(command_id)
            if item is not None and not item.future.done():
                item.delivered = True
                return {"command_id": command_id, "tool": "get_navigation_info", "arguments": {}}
        return None

    def complete(self, command_id: str, snapshot: NavigationSnapshot) -> bool:
        item = self.pending.get(command_id)
        if item is None or not item.delivered or item.future.done():
            return False
        item.future.set_result(snapshot)
        return True
