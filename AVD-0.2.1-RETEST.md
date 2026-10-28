# AVD 0.2.1: destination query correction

## 무엇을 수정했나

이전 테스트 앱은 `getRouteStateInfo()`의 `isRouting=false`를 받으면
`getDestinationInfo()`를 호출하지 않고 `no_destination`을 반환했습니다.
사용자가 확인한 내비게이션 경로 안내 화면과 앱 응답이 불일치했으므로, 이 단일 상태값을
목적지 조회의 선행 조건으로 사용하는 처리를 제거했습니다.

- 목적지 API를 직접 요청하고 실제 `onDestinationInfo` 응답을 기다립니다.
- `isRouting`, `naviMode`, 내비게이션 상태를 최근 SDK 이벤트 목록에 표시합니다.
- 목적지 콜백을 6초 안에 받지 못하면 `sdk_error`로 표시합니다. 미응답을 목적지 부재로 단정하지 않습니다.
- 조회 도중 명시적 경로 취소 이벤트를 받았을 때만 `no_destination`을 만듭니다.
- 모의 거리/시간이나 이전 조회 값을 대신 반환하지 않습니다.

SDK가 false를 보고한 원인과 실제 AVD의 목적지 콜백 동작은 아직 확인되지 않았습니다.
이 버전은 잘못된 조기 종료를 제거한 수정본이며, AVD 실데이터 성공 판정은 재검증 후에 가능합니다.

## 다운로드

- [0.2.1 APK](vehicle-mcp-avd-0.2.1-debug.apk)
- [0.2.1 전체 소스](HyundaiMCP-avd-0.2.1-source.zip)
- [수정된 코드](https://github.com/FirstF1ame/HyundaiMCP/blob/avd-test-artifacts/android/app/src/main/java/example/vehiclemcp/NavigationQuery.kt)

최신 기본 APK/소스 ZIP 링크도 0.2.1로 갱신했습니다.
원래 0.2.0은 `vehicle-mcp-avd-0.2.0-debug.apk`, `HyundaiMCP-avd-0.2.0-source.zip`에 보존했습니다.

## 재검증

1. 0.2.1 APK를 설치합니다. Android Studio에서 로컬 소스를 빌드했다면 새 소스의 android 프로젝트를 열어 재빌드해도 됩니다.
2. 내장 내비게이션에서 목적지를 설정하고 경로 안내 중인 화면을 확인합니다.
3. Vehicle MCP 앱으로 돌아와 연결을 기다린 뒤 목적지 조회 버튼을 누릅니다.
4. 성공 시 `status=ok`와 `destination_name`, `remaining_distance_m`, `remaining_duration_s`를 확인합니다.
5. 실패 시 앱의 **최근 SDK 이벤트 목록과 결과 JSON**을 함께 확인합니다. 토큰은 공유하지 않습니다.

`목적지 콜백 미수신`이면 SDK/내비 서비스의 응답 경로를 추가 진단해야 합니다.
화면의 23km·34분처럼 반올림된 값을 SDK의 m·초 값과 완전 일치하는지로만 판정하지 마세요.

APK 설치 시 서명 불일치가 나면 AVD 데이터를 초기화하지 말고 오류를 확인하세요.
이전에 클라우드에서 제공한 APK와 이 APK의 서명 인증서는 같습니다. 로컬 Android Studio에서
직접 빌드한 APK는 다른 개발 서명을 사용할 수 있습니다.

## 검사 결과

- Android JVM 테스트 18개 통과: 기존 6개 + 조회 회귀 12개.
- `isRouting=false`에서도 유효 목적지를 받으면 정상 반환하는 회귀 테스트 포함.
- 목적지 미응답, 진단 요청 실패, 명시적 취소, 목적지 변경, SDK 오류, 미리 도착한 오래된 콜백,
  동시 조회 직렬화, 호출자 취소, 권한 예외, Provider 종료 처리 검증.
- APK 빌드/서명 검사와 Android Lint 통과. Lint 오류·경고 0건.
- Python 기존 테스트 12개 통과. 이전 Python 모의 부하 측정 결과는 변경하지 않음.
- 실제 사용자 AVD에서의 목적지 조회·GPT API 전체 연동은 아직 미검증.

APK SHA256: `cd7e9cecbfac7520dd1feb3eccee91bf917170d6d9ac57b275160db73b0c14da`
