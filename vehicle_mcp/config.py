import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    mode: str
    mcp_token: str
    bridge_token: str
    timeout_seconds: float = 12.0
    port: int = 8000

    def __post_init__(self):
        if self.mode not in {"mock", "bridge"}:
            raise ValueError("VEHICLE_MODE must be mock or bridge")
        if min(len(self.mcp_token), len(self.bridge_token)) < 32:
            raise ValueError("Use separate randomly generated tokens of at least 32 characters")
        if self.mcp_token == self.bridge_token:
            raise ValueError("MCP and bridge tokens must differ")
        if not 0 < self.timeout_seconds <= 60:
            raise ValueError("Timeout must be greater than zero and at most 60 seconds")


def settings_from_env() -> Settings:
    load_dotenv()
    return Settings(
        mode=os.getenv("VEHICLE_MODE", "mock"),
        mcp_token=os.getenv("MCP_TOKEN", ""),
        bridge_token=os.getenv("BRIDGE_TOKEN", ""),
        timeout_seconds=float(os.getenv("COMMAND_TIMEOUT_SECONDS", "12")),
        port=int(os.getenv("PORT", "8000")),
    )
