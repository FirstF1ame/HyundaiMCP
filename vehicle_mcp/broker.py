import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import NavigationSnapshot


@dataclass
# 명령 하나의 응답 대기 객체. delivered는 Bridge에 실제 전달됐는지를 나타낸다.
class Pending:
    future: asyncio.Future
    delivered: bool = False


class Broker:
    """In-memory single-vehicle broker. One server worker only; no persistent location logs."""

    def __init__(self, timeout: float):
        self.timeout = timeout
        # UUID → 응답 대기 상태. 큐에는 UUID만 넣어 응답을 요청별로 연결한다.
        self.pending: dict[str, Pending] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=16)
        # 연결 상태 판단에는 시스템 시각 변경의 영향을 받지 않는 monotonic 시간을 쓴다.
        self.last_poll = 0.0

    # MCP 요청 → 명령 큐 등록 → 해당 UUID의 Future 응답 대기 → 유효한 결과 반환.
    async def query(self) -> dict:
        if time.monotonic() - self.last_poll > 20:
            return {"status": "bridge_offline", "source": "pleos_bridge"}
        # 최대 16개까지만 처리해 대기 요청이 무제한 쌓이지 않게 한다.
        if len(self.pending) >= 16 or self.queue.full():
            return {"status": "busy", "source": "pleos_bridge"}
        command_id = str(uuid.uuid4())
        item = Pending(asyncio.get_running_loop().create_future())
        self.pending[command_id] = item
        self.queue.put_nowait(command_id)
        try:
            snapshot = await asyncio.wait_for(item.future, timeout=self.timeout)
            # 데이터 조회 시각 기준: 30초 초과 과거 또는 5초 초과 미래는 사용할 수 없다.
            age = (datetime.now(timezone.utc) - snapshot.observed_at).total_seconds()
            if age > 30 or age < -5:
                return {"status": "stale_data", "source": "pleos_bridge"}
            return snapshot.model_dump(mode="json")
        except TimeoutError:
            return {"status": "timeout", "source": "pleos_bridge"}
        # 성공·시간 초과·취소 모두 대기 상태를 정리하며 모의 값으로 대체하지 않는다.
        finally:
            self.pending.pop(command_id, None)

    # Bridge의 long polling: 최대 10초 대기하고, 이미 만료된 명령은 건너뛴다.
    async def next_command(self) -> dict | None:
        # 연결 상태 판단에는 시스템 시각 변경의 영향을 받지 않는 monotonic 시간을 쓴다.
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

    # 전달된 유효 명령만 완료한다. 중복·미전달·만료 응답은 False로 거부한다.
    def complete(self, command_id: str, snapshot: NavigationSnapshot) -> bool:
        item = self.pending.get(command_id)
        if item is None or not item.delivered or item.future.done():
            return False
        item.future.set_result(snapshot)
        return True
