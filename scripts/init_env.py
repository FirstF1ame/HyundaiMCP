"""Run once from the project root. Secrets remain only in the ignored .env file."""
import secrets
from pathlib import Path

# 프로젝트 루트에서 실행한다. x 모드는 기존 .env가 있으면 실패해 덮어쓰기를 막는다.
path = Path(".env")
with path.open("x", encoding="utf-8") as output:
    # 서로 독립적인 난수 토큰을 생성한다. 실제 API 키는 생성하거나 출력하지 않는다.
    output.write(
        "VEHICLE_MODE=mock\nPORT=8000\nCOMMAND_TIMEOUT_SECONDS=12\n"
        f"MCP_TOKEN={secrets.token_urlsafe(32)}\n"
        f"BRIDGE_TOKEN={secrets.token_urlsafe(32)}\n"
        "OPENAI_API_KEY=\nOPENAI_MODEL=\n"
    )
# 지원되는 파일시스템에서는 소유자만 파일을 읽고 쓰도록 권한을 제한한다.
try:
    path.chmod(0o600)
except OSError:
    pass
print("Created .env. Existing files are never overwritten.")
