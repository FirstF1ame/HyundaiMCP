# Verification — 2026-10-27

- Python 3.12.14; official MCP Python SDK 1.30.0.
- `python -m pytest -q`: 12 passed.
- Actual local HTTP MCP initialization, tool discovery, tool calls and Bridge round trips tested.
- Authentication separation, unsupported tools, no destination, SDK error, unsupported data,
  stale/future data, invalid negative values, timeout, duplicate results and concurrent correlation tested.
- GPT host tested with fake model responses and a real local MCP server; no paid API request.
- `pip check`: no broken requirements.
- Pleos SDK/Emulator, Android Kotlin compilation, real GPT API, ChatGPT UI connectors,
  public deployment and physical vehicle controls: NOT verified / NOT included.
