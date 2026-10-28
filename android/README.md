# Pleos AVD 테스트 앱 — 0.2.1

검증 갱신(2026-10-28): 사용자 Pleos AVD에서 목적지 조회 및 PC MCP 왕복을 확인했습니다.
새 환경에서는 아래 절차로 재확인하세요. 근거와 GPT 진행 상태는 프로젝트 루트의 `TEAM_HANDOFF_0.2.1.md`에 정리했습니다.

Pleos Connect AVD에서 NaviHelper SDK 연결과 실제 콜백 데이터를 확인하는 읽기 전용 앱입니다.
Python 서버 없이도 앱의 **목적지·남은 거리·시간 조회** 버튼을 사용할 수 있습니다.
`source=pleos_sdk`는 SDK 경로의 응답이라는 뜻입니다. AVD의 데이터가 실제 차량 데이터라는 뜻은 아닙니다.

## 1. Android Studio에서 실행

1. 저장소의 **android 폴더**를 Open합니다. Python 프로젝트 루트가 아닙니다.
2. Gradle Sync를 완료합니다. SDK Platform 34 및 Build Tools 34.0.0이 필요합니다.
3. Gradle JDK는 **17 이상**으로 설정합니다. Gradle 8.9 / AGP 8.7.3을 사용합니다.
4. `app` 실행 구성을 선택하고 준비한 Pleos Connect AVD를 대상으로 Run합니다.
5. AVD의 기본 내비게이션 앱을 열고 필요한 약관/초기 설정을 완료한 뒤 목적지를 설정합니다.
6. Vehicle MCP 앱으로 돌아와 **NaviHelper 연결됨**을 확인하고 조회 버튼을 누릅니다.

목적지를 설정하는 API나 차량 제어 API는 이 앱에서 호출하지 않습니다.
SDK 연결은 화면이 보일 때 시작하고, 화면을 떠나면 해제합니다. 복귀 후 다시 조회하세요.

### 예상 결과

- `status=ok`: `destination_name`, `remaining_distance_m`, `remaining_duration_s` 표시.
- `status=no_destination`: 현재 조회 도중 명시적인 경로 취소 이벤트를 수신한 경우. `isRouting=false`만으로 이 상태를 만들지 않음.
- `status=sdk_error`: SDK 미연결, 권한 거부, 목적지 콜백 미수신, 잘못된 값 등. 응답이 없다는 이유로 목적지 부재를 단정하거나 mock 값으로 대체하지 않음.

0.2.1에서는 `getDestinationInfo()`를 직접 요청하며 경로 상태 응답은 진단에만 사용합니다.
화면의 최근 SDK 이벤트 목록에 `isRouting`, `naviMode`, 내비게이션 상태 및 목적지 콜백 수신 여부를 남깁니다.
내비게이션에 경로가 표시되는데 이전 버전에서 `no_destination`이 나왔다면 이 버전으로 재확인하세요.

SDK가 연결되지 않으면 AVD가 일반 Android 이미지가 아닌 Pleos 이미지인지,
기본 내비게이션 서비스가 실행됐는지 확인하세요. 퍼미션이 거부되면 SDK 사용 승인/AVD 권한 설정을
공식 가이드에 따라 확인하세요. 앱은 `pleos.car.permission.NAVI_ROUTE`만 선언합니다.
연결 직후 성공해도 서비스가 이후 끊기면 조회는 실패할 수 있습니다.

## 2. PC Python MCP 서버까지 연결하기 (선택)

**AVD가 실행 중인 같은 PC**에서 서버를 실행해야 합니다. `adb reverse`는 클라우드 서버로 연결하지 않습니다.
아래 Python 명령은 저장소 루트에서, Gradle 명령은 android 폴더에서 실행합니다.

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ".[test,gpt]"
# .env가 아직 없을 때만 실행 (기존 파일을 덮어쓰지 않음)
if (-not (Test-Path .env)) { .\.venv\Scripts\python.exe scripts/init_env.py }
$env:VEHICLE_MODE = "bridge"
.\.venv\Scripts\python.exe -m vehicle_mcp.server
```

macOS/Linux에서는 `.venv/bin/python`을 사용하고 `VEHICLE_MODE=bridge .venv/bin/python -m vehicle_mcp.server`로 실행합니다.

다른 터미널에서:

```text
adb devices
adb -s <AVD_SERIAL> reverse tcp:8000 tcp:8000
```

`adb`를 찾지 못하면 Android SDK의 `platform-tools` 폴더에 있는 실행 파일을 사용합니다.
`<AVD_SERIAL>`은 `adb devices`에서 확인한 값으로 바꾸세요.

1. PC의 로컬 `.env`에 있는 **BRIDGE_TOKEN**을 앱의 토큰 입력란에 넣습니다. `MCP_TOKEN`과 다릅니다.
2. **Bridge 시작**을 누릅니다. 토큰은 저장하지 않으며 화면을 떠나면 지웁니다.
3. PC의 다른 터미널에서 `.venv`의 Python으로 `-m vehicle_mcp.client`를 실행합니다.
4. 앱에 명령 수신/결과 전송 상태가, PC에 `source=pleos_sdk`인 결과가 표시되는지 확인합니다.

서버 PORT는 기본 8000을 사용하세요. 다른 포트는 이 앱에서 설정하지 않습니다.
Python `scripts/mock_bridge.py`와 앱 Bridge는 **동시에 실행하지 마세요**. 둘이 명령을 나눠 받아 검증이 섞입니다.
서버의 기본 명령 대기는 12초이며 SDK 조회 대기는 6초입니다. 너무 짧게 변경하면 서버에서 먼저 만료될 수 있습니다.
인증 오류는 토큰, 409는 서버 bridge 모드, 연결 실패는 서버 실행/adb reverse를 확인하세요.

## 3. 빌드 및 자동 검사

android 폴더에서 실행합니다. Windows에서는 `gradlew.bat`, macOS/Linux에서는 `./gradlew`를 사용합니다.

```text
gradlew.bat :app:assembleDebug :app:testDebugUnitTest :app:lintDebug
```

APK: `app/build/outputs/apk/debug/app-debug.apk`
JUnit 결과: `app/build/reports/tests/testDebugUnitTest/index.html`
자동 검사는 응답 매핑·단위·오류 데이터 제외·HTTP Bridge ID/인증/오류 처리를 검증합니다.
AVD의 Navi Service와 실제 연결은 위 수동 절차로 별도 확인해야 합니다.

## SDK 근거 및 제약

공식 Maven 배포의 `NaviHelper:3.0.5`와 전이 의존성 `navi-data:3.0.4`의 source JAR를 확인했습니다.

| 순서 | 공개 API / 콜백 | 사용하는 값 |
| --- | --- | --- |
| 연결 | `NaviHelper(context).initialize(onConnected, onFailed)` | SDK 연결 성공/실패 |
| 경로 진단 | `getRouteStateInfo()` → `onRouteStateInfo(RouteStateInfo)` | `isRouting`, `naviMode`; 목적지 조회 gate로 사용하지 않음 |
| 목적지 조회 | `getDestinationInfo()` → `onDestinationInfo(DestinationInfo)` | `name`, `remainDistance`(m), `remainTime`(s) |
| 종료 | `removeListener()` → `release()` | 리소스 정리 |

`observed_at`은 이 앱이 목적지 콜백을 받은 시각입니다. SDK 데이터에는 원본 관측 시각이 없어
센서 측정 시각/SDK 내부 데이터 나이를 증명하지 못합니다. 콜백에 요청 ID도 없어 앱의 조회를 직렬화하고
매번 요청 후 응답을 기다리지만, SDK가 지연/재전송한 이벤트인지 엄밀히 구분할 수는 없습니다.
PC와 AVD의 시계를 맞추세요. Python 서버는 30초보다 오래됐거나 5초 넘게 미래인 결과를 거부합니다.

토큰·목적지는 로그에 남기지 않으며 결과는 화면/메모리에서만 유지합니다.
로컬 HTTP는 debug 빌드의 127.0.0.1에만 허용합니다. 공개 배포·백그라운드 실행·실차 검증은 범위 밖입니다.

공식 문서:
- https://document.pleos.ai/docs/pleos-only/connect-sdk-pleos/NaviHelper/importing-sdk
- https://document.pleos.ai/docs/pleos-only/connect-sdk-pleos/NaviHelper/initialization-and-release
- https://document.pleos.ai/docs/pleos-only/connect-sdk-pleos/NaviHelper/destinations
- https://document.pleos.ai/docs/pleos-only/connect-sdk-pleos/NaviHelper/declaring-permissions
