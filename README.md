# Pleos AVD test app downloads

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
Real Pleos AVD destination callbacks and live GPT API integration still require verification.

Latest APK SHA256: `cd7e9cecbfac7520dd1feb3eccee91bf917170d6d9ac57b275160db73b0c14da`

The original 0.2.0 APK/source are preserved under versioned filenames.
`vehicle-mcp-avd-debug.apk` and `HyundaiMCP-avd-test-source.zip` now refer to 0.2.1.
The source ZIP contains all current code. Only the new/changed query files are additionally
published as plain files for review; this branch is not a complete project checkout.
The application source updates have not been merged into main.
