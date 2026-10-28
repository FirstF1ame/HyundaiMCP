# Pleos AVD test app downloads

- vehicle-mcp-avd-debug.apk: installable debug APK
- HyundaiMCP-avd-test-source.zip: complete matching source; Android Studio project is in android/

Open the APK file on GitHub and use Download raw file.

APK SHA256: ec9befb6742cac5a55c7608f0b6a092e06c9cc12b462d414890334abeb73a757

Validated: APK compilation/signature, 6 Android JVM tests, 12 Python tests and Android Lint.
Not validated here: execution on Pleos AVD / Navi Service and physical vehicles.

Install APK, set a destination in Pleos Navigation, then open Vehicle MCP and query navigation.
See android/README.md inside the source ZIP for SDK/Bridge testing instructions.

The source ZIP includes Android changes not yet committed to main.
This branch contains downloadable build artifacts only; main is unchanged.
