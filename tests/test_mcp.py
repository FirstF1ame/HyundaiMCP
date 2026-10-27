import asyncio
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from vehicle_mcp.config import Settings
from vehicle_mcp.server import create_app


# 테스트마다 임시 포트에 실제 HTTP 서버를 띄우고 종료 시 정리하는 공통 도우미.
@asynccontextmanager
async def running(mode="mock", timeout=1):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    settings = Settings(mode, "m" * 40, "b" * 40, timeout_seconds=timeout, port=port)
    server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level="error", access_log=False))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("Server did not start")
                await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{port}", settings
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 15)
        sock.close()


# 공식 MCP 클라이언트로 인증·초기화까지 수행해 직접 함수 호출만으로는 놓칠 통신 오류를 검증한다.
@asynccontextmanager
async def session_at(url, token):
    async with httpx.AsyncClient(trust_env=False, headers={"Authorization": f"Bearer {token}"}) as http:
        async with streamable_http_client(url + "/mcp", http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


# 상태와 데이터 나이를 바꿔 성공·오류·과거/미래 시각 응답을 만드는 테스트 전용 데이터.
def snapshot(status="ok", age=0):
    data = {"source": "mock_bridge", "status": status,
            "observed_at": (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()}
    if status == "ok":
        data.update(destination_name="서울역", remaining_distance_m=3210, remaining_duration_s=420)
    return data


# 도구 발견, 읽기 전용 힌트, 결과 단위, 미등록 도구 거부를 함께 검증한다.
async def test_actual_mcp_discovery_call_and_no_arbitrary_tools():
    async with running() as (url, cfg), session_at(url, cfg.mcp_token) as session:
        tools = (await session.list_tools()).tools
        assert [t.name for t in tools] == ["get_navigation_info"]
        assert tools[0].annotations.readOnlyHint is True
        result = await session.call_tool("get_navigation_info", {})
        assert not result.isError
        assert result.structuredContent["source"] == "mock"
        assert result.structuredContent["remaining_duration_s"] == 1080
        assert (await session.call_tool("set_destination", {})).isError


# 토큰 누락 및 MCP/Bridge 토큰의 교차 사용이 차단되는지 확인한다.
async def test_role_tokens_and_missing_credentials():
    async with running() as (url, cfg), httpx.AsyncClient(trust_env=False, base_url=url) as http:
        assert (await http.get("/health")).status_code == 401
        assert (await http.get("/bridge/commands", headers={"Authorization": f"Bearer {cfg.mcp_token}"})).status_code == 401
        assert (await http.post("/mcp", headers={"Authorization": f"Bearer {cfg.bridge_token}"})).status_code == 401
        assert (await http.get("/health", headers={"Authorization": f"Bearer {cfg.mcp_token}"})).status_code == 200


# Bridge 미접속 시 mock 성공 값으로 대체하지 않는지 검증한다.
async def test_bridge_offline_never_falls_back_to_mock():
    async with running("bridge") as (url, cfg), session_at(url, cfg.mcp_token) as session:
        result = (await session.call_tool("get_navigation_info", {})).structuredContent
        assert result == {"status": "bridge_offline", "source": "pleos_bridge"}


# 아래 6가지 상태/시각 조합을 각각 독립된 테스트로 실행한다.
@pytest.mark.parametrize("status,age,expected", [
    ("ok", 0, "ok"), ("no_destination", 0, "no_destination"),
    ("sdk_error", 0, "sdk_error"), ("unsupported", 0, "unsupported"),
    ("ok", 60, "stale_data"), ("ok", -60, "stale_data"),
])
# MCP 호출 → Bridge 명령 수신 → 결과 POST → MCP 결과 반환과 중복 응답 거부를 확인한다.
async def test_mcp_to_bridge_round_trip(status, age, expected):
    async with running("bridge", timeout=3) as (url, cfg):
        async with httpx.AsyncClient(trust_env=False, base_url=url, headers={"Authorization": f"Bearer {cfg.bridge_token}"}) as bridge:
            poll = asyncio.create_task(bridge.get("/bridge/commands", timeout=12))
            # Establishing an MCP session gives the bridge poll time to reach the server.
            async with session_at(url, cfg.mcp_token) as session:
                call = asyncio.create_task(session.call_tool("get_navigation_info", {}))
                command = (await poll).json()
                assert command["tool"] == "get_navigation_info"
                payload = {"command_id": command["command_id"], "result": snapshot(status, age)}
                assert (await bridge.post("/bridge/results", json=payload)).status_code == 200
                result = (await call).structuredContent
                assert result["status"] == expected
                if expected == "ok":
                    assert result["remaining_distance_m"] == 3210
                    assert result["source"] == "mock_bridge"
                else:
                    assert result.get("remaining_distance_m") is None
                # Replaying or submitting an expired command must not overwrite data.
                assert (await bridge.post("/bridge/results", json=payload)).status_code == 409


# 잘못된 음수 값은 422로 거부하고, 유효한 응답이 없으면 요청이 시간 초과되는지 확인한다.
async def test_invalid_bridge_data_and_timeout():
    async with running("bridge", timeout=0.5) as (url, cfg):
        async with httpx.AsyncClient(trust_env=False, base_url=url, headers={"Authorization": f"Bearer {cfg.bridge_token}"}) as bridge:
            poll = asyncio.create_task(bridge.get("/bridge/commands", timeout=12))
            async with session_at(url, cfg.mcp_token) as session:
                call = asyncio.create_task(session.call_tool("get_navigation_info", {}))
                command = (await poll).json()
                invalid = snapshot()
                invalid["remaining_duration_s"] = -1
                response = await bridge.post("/bridge/results", json={"command_id": command["command_id"], "result": invalid})
                assert response.status_code == 422
                assert (await call).structuredContent["status"] == "timeout"


# 두 요청에 역순으로 응답해도 command_id에 따라 올바른 호출자에게 돌아가는지 확인한다.
async def test_concurrent_calls_keep_their_own_results():
    async with running("bridge", timeout=3) as (url, cfg):
        async with httpx.AsyncClient(trust_env=False, base_url=url, headers={"Authorization": f"Bearer {cfg.bridge_token}"}) as bridge:
            poll = asyncio.create_task(bridge.get("/bridge/commands", timeout=12))
            async with session_at(url, cfg.mcp_token) as session:
                first = asyncio.create_task(session.call_tool("get_navigation_info", {}))
                command1 = (await poll).json()
                second = asyncio.create_task(session.call_tool("get_navigation_info", {}))
                command2 = (await bridge.get("/bridge/commands")).json()
                assert command1["command_id"] != command2["command_id"]
                for command, distance in [(command2, 222), (command1, 111)]:
                    data = snapshot()
                    data["remaining_distance_m"] = distance
                    assert (await bridge.post("/bridge/results", json={"command_id": command["command_id"], "result": data})).status_code == 200
                assert (await first).structuredContent["remaining_distance_m"] == 111
                assert (await second).structuredContent["remaining_distance_m"] == 222
