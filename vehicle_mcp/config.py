import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
# 서버와 클라이언트가 공유하는 실행 설정. frozen=True로 생성 후 변경을 막는다.
class Settings:
    # mock: 고정 시뮬레이션 / bridge: 외부 Bridge가 조회 결과를 반환하는 모드.
    mode: str
    # MCP 호출자와 Bridge의 인증 토큰을 분리해 서로 다른 경로에 접근하지 못하게 한다.
    mcp_token: str
    bridge_token: str
    # 명령 하나의 결과를 기다리는 최대 시간(초)과 로컬 HTTP 수신 포트.
    timeout_seconds: float = 12.0
    port: int = 8000

    # 시작 단계에서 모드·토큰 길이/중복·대기 시간을 검증한다.
    def __post_init__(self):
        if self.mode not in {"mock", "bridge"}:
            raise ValueError("VEHICLE_MODE must be mock or bridge")
        if min(len(self.mcp_token), len(self.bridge_token)) < 32:
            raise ValueError("Use separate randomly generated tokens of at least 32 characters")
        if self.mcp_token == self.bridge_token:
            raise ValueError("MCP and bridge tokens must differ")
        if not 0 < self.timeout_seconds <= 60:
            raise ValueError("Timeout must be greater than zero and at most 60 seconds")


# .env를 읽되 이미 주입된 환경변수를 우선하며, 누락된 필수 토큰은 Settings에서 거부한다.
def settings_from_env() -> Settings:
    load_dotenv()
    return Settings(
        mode=os.getenv("VEHICLE_MODE", "mock"),
        mcp_token=os.getenv("MCP_TOKEN", ""),
        bridge_token=os.getenv("BRIDGE_TOKEN", ""),
        timeout_seconds=float(os.getenv("COMMAND_TIMEOUT_SECONDS", "12")),
        port=int(os.getenv("PORT", "8000")),
    )
