"""No paid OpenAI requests. Test the local GPT-host/MCP boundary with a fake model."""
import json
from types import SimpleNamespace

import pytest

from vehicle_mcp.client import ask_gpt
from test_mcp import running


# GPT 응답만 가짜로 교체하고 실제 로컬 MCP 왕복은 유지한다. API 요금 없이 Host 경계를 검증한다.
async def test_model_call_reaches_real_mcp_and_result_returns(monkeypatch, capsys):
    openai = pytest.importorskip("openai")
    requests = []

    # 첫 응답은 함수 호출 요청, 두 번째 응답은 MCP 결과를 받은 뒤의 자연어 답변이다.
    class FakeResponses:
        async def create(self, **kwargs):
            requests.append(kwargs)
            if len(requests) == 1:
                return SimpleNamespace(output=[SimpleNamespace(
                    type="function_call", name="get_navigation_info", arguments="{}", call_id="call_test",
                )], output_text="")
            returned = kwargs["input"][-1]
            assert returned["type"] == "function_call_output"
            assert returned["call_id"] == "call_test"
            data = json.loads(returned["output"])
            assert data["structuredContent"]["source"] == "mock"
            assert data["structuredContent"]["remaining_duration_s"] == 1080
            return SimpleNamespace(output=[], output_text="시뮬레이션 데이터 기준 18분입니다.")

    # AsyncOpenAI의 컨텍스트 관리자 형태만 흉내 내 외부 API 연결을 방지한다.
    class FakeAI:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    # 테스트 종료 시 monkeypatch가 교체한 객체와 환경변수를 원래대로 복구한다.
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAI)
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder-not-a-real-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    async with running() as (_, cfg):
        monkeypatch.setenv("MCP_TOKEN", cfg.mcp_token)
        monkeypatch.setenv("BRIDGE_TOKEN", cfg.bridge_token)
        monkeypatch.setenv("PORT", str(cfg.port))
        await ask_gpt("얼마나 남았어?")
    assert len(requests) == 2
    assert requests[0]["tools"][0]["name"] == "get_navigation_info"
    assert "시뮬레이션" in capsys.readouterr().out
