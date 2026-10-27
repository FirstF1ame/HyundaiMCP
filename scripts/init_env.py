"""Run once from the project root. Secrets remain only in the ignored .env file."""
import secrets
from pathlib import Path

path = Path(".env")
with path.open("x", encoding="utf-8") as output:
    output.write(
        "VEHICLE_MODE=mock\nPORT=8000\nCOMMAND_TIMEOUT_SECONDS=12\n"
        f"MCP_TOKEN={secrets.token_urlsafe(32)}\n"
        f"BRIDGE_TOKEN={secrets.token_urlsafe(32)}\n"
        "OPENAI_API_KEY=\nOPENAI_MODEL=\n"
    )
try:
    path.chmod(0o600)
except OSError:
    pass
print("Created .env. Existing files are never overwritten.")
