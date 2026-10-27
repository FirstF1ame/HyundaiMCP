"""Transport simulator only. Not a Pleos SDK implementation. Never use for live evidence."""
import asyncio
from datetime import datetime, timezone

import httpx

from vehicle_mcp.config import settings_from_env


# 실제 SDK 없이 Bridge의 폴링·명령 ID 연결·결과 반환 경로만 검증하는 시뮬레이터.
async def main():
    settings = settings_from_env()
    if settings.mode != "bridge":
        raise SystemExit("Set VEHICLE_MODE=bridge and restart the server first")
    print("SIMULATED BRIDGE: synthetic data; no Pleos connection")
    async with httpx.AsyncClient(trust_env=False, 
        base_url=f"http://127.0.0.1:{settings.port}",
        headers={"Authorization": f"Bearer {settings.bridge_token}"}, timeout=15,
    ) as http:
        # long polling으로 받은 명령에 같은 command_id를 넣어 합성 데이터를 돌려준다.
        while True:
            response = await http.get("/bridge/commands")
            if response.status_code == 204:
                continue
            response.raise_for_status()
            command = response.json()
            result = await http.post("/bridge/results", json={
                "command_id": command["command_id"],
                "result": {
                    "source": "mock_bridge", "status": "ok",
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "destination_name": "서울역 (Bridge 통신 시뮬레이션)",
                    "remaining_distance_m": 12300, "remaining_duration_s": 1080,
                },
            })
            # 서버에서 이미 만료된 요청(409)은 건너뛰고 그 외 HTTP 오류는 드러낸다.
            if result.status_code != 409:
                result.raise_for_status()


if __name__ == "__main__":
    asyncio.run(main())
