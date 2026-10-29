# Pleos AVD test app downloads

**최신 팀 공유 문서:** [Vehicle MCP 0.2.1 인수인계 및 검증 보고서](TEAM_HANDOFF_0.2.1.md). 사용자 AVD의 SDK–MCP 왕복 성공 및 OpenAI 크레딧 오류까지 반영했습니다.

Latest: **0.2.1-avd**, versionCode 2.

- [Download APK](vehicle-mcp-avd-0.2.1-debug.apk)
- [Download matching complete source](HyundaiMCP-avd-0.2.1-source.zip)
- [0.2.1 fix and AVD retest instructions](AVD-0.2.1-RETEST.md)
- [MCP benchmark / code responsibilities report](MCP_VALIDATION_REPORT.md)
- [Original mock Bridge benchmark JSON](docs/benchmarks/bridge-c16-1000-r1.json)
- [Python benchmark script](benchmark_mcp.py)
- [Windows benchmark instructions](MCP-BENCHMARK-GUIDE.md)

0.2.1 removes an application-level early return that prevented destination queries when
`isRouting=false`. It requests destination data directly, reports recent SDK diagnostic events,
and returns an error when no callback arrives instead of assuming no destination.

Validated: APK build/signature, 18 Android JVM tests, 12 Python tests, Android Lint (0 findings).
User verified Pleos AVD destination callbacks and direct PC MCP round trips. OpenAI API returned a credit-balance error; live GPT tool calling and final answers remain unverified.

Latest APK SHA256: `cd7e9cecbfac7520dd1feb3eccee91bf917170d6d9ac57b275160db73b0c14da`

The original 0.2.0 APK/source are preserved under versioned filenames.
`vehicle-mcp-avd-debug.apk` and `HyundaiMCP-avd-test-source.zip` now refer to 0.2.1.
The source ZIP contains all current code. Only the new/changed query files are additionally
published as plain files for review; this branch is not a complete project checkout.
The application source updates have not been merged into main.

## 프로젝트 비교

[HyundaiMCP와 HyeeSeong/pleostest 비교 보고서](COMPARISON_PLEOSTEST_20261029.md) — 2026-10-29, 친구 main `0d288c8` 코드와 우리 0.2.1 비교.
