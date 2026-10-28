# Latest user verification — 2026-10-28

- User confirmed destination callbacks in the Pleos AVD with the 0.2.1 test app.
- Two direct PC MCP calls returned `source=pleos_sdk`, `status=ok`, `isError=false`,
  destination information, 23000 m and 1860 s; callback receipt timestamps changed.
- This validates the observed AVD SDK → Android Bridge → Python MCP round trip,
  not physical vehicle data freshness or long-duration reliability.
- The live GPT attempt reached OpenAI Responses API and received HTTP 429,
  type `insufficient_quota`, code `credit_balance_exhausted`.
- Model execution, model eligibility and GPT-initiated tool calling/final answers remain unverified.
- See TEAM_HANDOFF_0.2.1.md and docs/evidence/ for redacted user-provided evidence summaries.
- These are user-local observations; prior automated test results were not rerun solely for this documentation update.

## Prior implementation and test records (historical)

# AVD 0.2.1 destination-query correction — 2026-10-28

- Fixed an application-level early return: `isRouting=false` no longer prevents `getDestinationInfo()`.
- Destination callbacks drive the result. No callback produces `sdk_error`, not assumed `no_destination`.
- Route state and navigation status are retained as recent on-screen diagnostics without tokens or coordinates.
- Added 12 coroutine-based query regression tests; Android JVM suite now has 18 tests.
- Regression scenarios include false isRouting with a valid destination, missing/failed route diagnostics,
  callback timeout, explicit route cancellation, destination changes, SDK errors, stale pre-query callbacks,
  serialized concurrent queries, caller cancellation, permission exception and provider shutdown.
- Debug APK compilation, Android Lint and 18 JVM tests passed in the cloud build environment.
- Python regression suite still has 12 tests; previous mock Bridge benchmark data is unchanged.
- User confirmed SDK connection in Pleos AVD, but real destination callback success with 0.2.1 remains
  pending a test on the user's AVD. Do not claim SDK/AVD end-to-end readiness from these unit tests.

## Earlier build records (historical)

# AVD test app verification — 2026-10-27

- Android debug APK built with Gradle 8.9, AGP 8.7.3, Kotlin 1.9.25, JDK 21 and Android SDK 34.
- Official Maven dependency: `ai.pleos.playground:NaviHelper:3.0.5` (`navi-data:3.0.4`).
- SDK callback signatures and destination fields/units checked against official source JARs.
- `:app:testDebugUnitTest`: 6 passed, 0 failed, 0 skipped. Covers result mapping/units,
  invalid data, failure fields, Bridge request IDs, Bearer authentication and wrong server mode.
- HTTP Bridge tests use a local MockWebServer, not a Pleos AVD or a live Python server.
- `:app:assembleDebug` and `:app:lintDebug` passed; APK signature verified with apksigner.
- Python regression suite: 12 passed; `pip check`: no broken requirements.
- AVD installation, Navi Service connection, SDK permission grants and SDK-to-Python end-to-end
  execution: NOT executed here; follow `android/README.md` on the PC hosting the AVD.
- Live GPT API and physical vehicle behavior: NOT verified.
- `observed_at` is callback receipt time; SDK source data age cannot be independently verified.

## Previous Python-only baseline

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
