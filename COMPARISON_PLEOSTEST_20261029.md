# HyundaiMCP 0.2.1과 pleostest 비교 보고서

작성일: 2026-10-29 (한국 시간)

## 1. 결론

**두 프로젝트는 Pleos 데이터를 MCP 도구로 제공한다는 목표가 같지만, 조회 대상과 AI 앱 연결 방식이 다르다.**

- **우리 HyundaiMCP:** NaviHelper로 목적지·남은 거리·시간을 읽는 Android 앱 + Python HTTP MCP 서버. 실제 SDK–PC MCP 왕복과 모의 부하 측정은 확인했지만, GPT 최종 답변은 API 크레딧 부족/ChatGPT 터널 준비 문제로 아직 미검증이다.
- **친구 pleostest:** Vehicle SDK로 문·창문·에너지를 읽는 Android 앱 + Node.js stdio MCP 서버. 결과 보고서에는 ChatGPT·Claude 데스크톱의 실제 도구 호출·답변과 화면을 내린 상태의 조회 성공이 기록되어 있다. 이번 비교에서 그 사용자 실행을 독립적으로 재현한 것은 아니다.

우리 프로젝트에 바로 참고할 부분은 **데스크톱용 stdio 연결 방식, Foreground Service의 수명 주기, 여러 항목의 부분 성공 계약**이다. 친구 프로젝트에 제공할 수 있는 것은 **내비게이션 조회 도메인, 역할별 토큰 인증, 반복 측정 도구와 원본 성능 자료**다.

## 2. 비교 기준과 확인 방법

| 항목 | 기준 |
| --- | --- |
| 친구 저장소 | `HyeeSeong/pleostest` |
| 친구 확인 커밋 | `0d288c8aeab3b2fd08d09a257d894cbfeca793ca` (`main`) |
| 우리 코드 | 현재 작업 공간의 Android `0.2.1-avd` 및 Python 구현 |
| 우리 최신 팀 문서 | [TEAM_HANDOFF_0.2.1.md](TEAM_HANDOFF_0.2.1.md) |
| 우리 main 기준 | `771a0a7683756c9a4b13f4fa92567db0552c212a` — 최신 Android 전체 소스는 아직 main에 병합되지 않음 |
| 우리 전체 Android 소스 | [0.2.1 ZIP](https://raw.githubusercontent.com/FirstF1ame/HyundaiMCP/avd-test-artifacts/HyundaiMCP-avd-0.2.1-source.zip) |
| 검토 방식 | 친구 코드를 /tmp의 별도 디렉터리에서 읽기 전용으로 검토. 양쪽 코드와 보고서 대조 |
| 실행 범위 | 이번 비교를 위해 친구 앱 설치, SDK·AI 앱 호출, Gradle/npm 테스트를 새로 실행하지 않음 |

친구 저장소의 `POC-REPORT.md`에 적힌 실행 성공과 테스트 통과 수는 **친구 측 보고 기록**이다. 코드상 구현 여부와 해당 문서의 실측 보고를 구분한다. 친구의 Linear 링크는 이번에 조회하거나 변경하지 않았다.

## 3. 핵심 차이 표

| 기준 | 우리 HyundaiMCP | 친구 pleostest |
| --- | --- | --- |
| 조회 대상 | 내비게이션 목적지·남은 거리·시간 | 문 위치/잠금, 창문 위치, 연료·EV 배터리 |
| Pleos SDK | NaviHelper 3.0.5, navi-data 3.0.4 | Vehicle 2.3.2 |
| 내장 내비게이션 의존 | 있음: Navi Service와 호환 내비 앱 필요 | 차량 상태 조회에는 내비 앱 불필요; Vehicle Service/capability 필요 |
| MCP 도구 수 | 1개 | 4개 |
| MCP 구현 | Python `mcp==1.30.0`, FastMCP | Node.js `@modelcontextprotocol/server==2.4.0`, zod |
| MCP 전송 | Streamable HTTP `/mcp` | stdio: AI 앱이 로컬 MCP 프로세스를 실행 |
| Android Bridge 역할 | HTTP 클라이언트: PC에 poll·결과 POST | HTTP 서버: PC 요청에 응답 |
| Bridge 경로 | GET `/bridge/commands`, POST `/bridge/results` | POST `/v2/vehicle-read` |
| ADB 연결 | `reverse tcp:8000 tcp:8000` | `forward tcp:18765 tcp:18765` |
| AI 연결 | Python Responses API Host 구현; ChatGPT 웹 터널 설정 진행 중 | ChatGPT/Claude 데스크톱 로컬 stdio 등록 방식 |
| 별도 OpenAI API 사용 | `client.py --ask`에서 사용 | 프로젝트 코드에는 사용하지 않음. 모델 실행은 AI 앱이 담당 |
| 연결 인증 | MCP_TOKEN과 BRIDGE_TOKEN 분리 | Bridge 토큰 없음. loopback·Host·Origin 검사 |
| Android 수명 주기 | Activity가 숨겨지면 SDK/Bridge 중지·토큰 삭제 | Foreground Service가 SDK/Bridge 유지; 알림/버튼으로 중지 |
| 동시성 | 서버 pending/queue 최대 16, Android SDK 조회는 Mutex 직렬화 | 공통 reader 단일 슬롯. 이미 조회 중이면 BUSY |
| SDK 요청 제한 | 목적지 콜백 6초; PC Broker 기본 12초 등 구간별 제한 | 도구 처리 총 10초 기한을 PC→Android에 잔여 시간으로 전달 |
| 다중 항목 실패 | 한 내비 스냅샷의 status로 표현 | 항목별 상태 및 COMPLETE/PARTIAL/FAILED |
| UI 수동 버튼 | 목적지 조회 및 Bridge 시작/중지 | 앞좌측 문 조회 및 서비스 중지; MCP는 더 많은 도메인 제공 |
| 전체 코드 공유 | 최신 앱은 ZIP, artifact 브랜치는 일부 소스/문서; main 정리 필요 | 확인한 main에 Android와 mcp 코드가 함께 존재 |

SDK 버전 번호 1.x/2.x/3.x는 언어·제품이 다른 라이브러리의 버전이다. 이 숫자만으로 호환성이나 완성도를 비교하지 않는다.

## 4. 구조에서 가장 큰 차이: 누가 누구에게 요청하는가

### 4.1 우리 구조

```text
[직접 호출] PC Python MCP 클라이언트
[API 경로]  Python GPT Host → OpenAI Responses API
                    ↓ 도구 실행
           PC Python MCP 서버 (/mcp)
                    ↓ Broker 명령 대기열
           Android가 GET으로 명령 poll
                    ↓
           NavigationQuery → NaviHelper → 내장 내비게이션
                    ↓
           Android가 POST로 결과 반환
```

- PC 서버가 HTTP 진입점과 요청 대기 상태를 가진다.
- Android는 명령을 받으러 PC에 접속한다.
- AVD의 localhost:8000을 PC 서버로 보내기 위해 `adb reverse`를 사용한다.
- Python API Host가 모델 요청과 MCP 실행을 모두 조정한다.

### 4.2 친구 구조

```text
ChatGPT 또는 Claude 데스크톱
        ↓ stdio로 앱별 로컬 프로세스 실행
Node.js MCP 서버 (mcp/src/server.mjs)
        ↓ PC localhost:18765, HTTP POST 1회
adb forward
        ↓ Android localhost:18765
BridgeService → DoorBridgeServer → VehicleStatusReader
        ↓
PleosVehicleSdk → Vehicle SDK / Vehicle Service
        ↓ 응답을 같은 HTTP 요청으로 반환
AI 앱이 결과를 받아 답변
```

- Android가 직접 HTTP 서버를 연다.
- PC Node 서버가 Android에 요청을 보낸다.
- `adb forward`로 PC 요청을 AVD 내부로 전달한다.
- 각 AI 앱이 자신만의 Node stdio 프로세스를 실행하지만 같은 Android reader를 공유한다.
- 이 HTTP POST는 프로젝트 내부 Bridge 계약이다. AI 앱과 MCP 사이의 HTTP 전송이라는 뜻은 아니다.

근거: [친구 MCP 서버](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/mcp/src/server.mjs), [Bridge HTTP 클라이언트](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/mcp/src/vehicle-client.mjs), [AI 앱 등록 설명](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/README.md#ai-앱-mcp-연결--사용자-설정-안내-hye-31-hye-34-hye-35).

## 5. 공통점

1. **별도 Android 앱에서 공식 SDK로 읽는다.** 둘 다 내장 내비게이션이나 차량 플랫폼 자체를 수정한 소스 프로젝트는 아니다.
2. **읽기 전용 PoC다.** 현재 노출 도구는 조회 기능이며, 차량 제어용 SET 기능을 구현하지 않는다.
3. **Android–PC Bridge와 공식 MCP SDK를 사용한다.** 자체 HTTP는 기기 통신, MCP는 AI/클라이언트 도구 호출을 담당한다.
4. **모델에 임의 영역·API·타임아웃을 넘기지 않는다.** 고정 도구와 빈 인자를 사용한다.
5. **지원 실패/미응답을 정상값으로 바꾸지 않는다.** 상태와 오류를 결과로 드러낸다.
6. **요청별 식별과 비동기 수명 주기를 관리한다.** 우리 Broker는 UUID/Future, 친구는 requestId/ticket/stage를 사용한다.
7. **콜백 수신 시각과 차량 원본 측정 시각을 구분한다.** 어느 쪽도 단순 수신 시각으로 물리 데이터 최신성을 보장하지 않는다.
8. **실차 검증은 아니다.** 두 프로젝트 모두 지금 근거는 Pleos AVD 및 로컬 테스트다.
9. **가짜 SDK/HTTP 경계로 자동 테스트한다.** 빌드 성공과 실제 SDK·AI 호출 성공을 별도로 기록한다.

## 6. 기능 도메인 차이

### 6.1 우리: NaviHelper

- 도구: `get_navigation_info`.
- 값: `destination_name`, `remaining_distance_m`, `remaining_duration_s`, `observed_at`.
- 0.2.1에서는 `getDestinationInfo()`의 실제 응답을 우선한다.
- `isRouting=false`를 이유로 목적지 API 호출을 생략하던 처리를 제거했다.
- 목적지 콜백이 없으면 6초 후 sdk_error로 처리하고, 명시적인 경로 취소 이벤트와 구분한다.
- 사용자 PC에서 `source=pleos_sdk`, `status=ok`, `isError=false` 결과 두 번을 확인했다.

### 6.2 친구: Vehicle SDK

| 도구 | 요청 집합 | 문서상 실제 결과 |
| --- | --- | --- |
| `get_door_status` | 문 4영역 위치 + 잠금 4영역, 총 8항목 | 위치 변화 확인 보고. 잠금은 AREA_UNSUPPORTED 보고 |
| `get_window_status` | 창문 4영역 위치 | raw 0→10 변화 확인 보고. 임의 %로 해석하지 않음 |
| `get_energy_level` | 연료 % + EV 배터리 % | EV 73%→35% 변화 보고. 연료는 CAPABILITY_FAILED |
| `get_front_left_door_position` | 앞좌측 문 위치 한 항목 | 기존 도구와 새 문 상태 도구의 값 일치 보고 |

**4개 도구가 등록되어 있다는 사실과 모든 항목이 정상 지원된다는 사실은 다르다.** 실패 항목이 섞이면 PARTIAL/FAILED로 보존한다.

친구 `PleosVehicleSdk`는 먼저 capability/access/area/bounds를 확인하고 공개 getter를 호출한다. 문·창문 묶음 영역을 단독 영역으로 임의 분해하지 않는다. 우리 NaviHelper의 API/콜백 계약과는 다른 SDK이므로 이 로직을 그대로 대체하면 안 된다.

근거: [VehicleStatusReader](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/app/src/main/java/com/example/pleostest/vehicle/VehicleStatusReader.kt), [PleosVehicleSdk](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/app/src/main/java/com/example/pleostest/vehicle/PleosVehicleSdk.kt).

## 7. AI 연결 차이가 지금 우리에게 중요한 이유

친구 README는 **ChatGPT 데스크톱의 STDIO 등록 화면을 사용자가 확인한 환경**을 전제로 한다. Claude도 로컬 Node 실행 명령을 등록한다. 친구 결과 보고서는 두 AI 앱에서 실제 값을 받아 답했다고 기록한다.

우리가 지금 진행한 ChatGPT 화면은 **서버 URL/터널 선택 화면**이었다. 이 화면에 Node/Python 실행 경로를 넣는 것으로 로컬 stdio 프로세스를 실행할 수는 없다.

따라서 친구가 API 키 없이 성공한 것은, 저장소 코드상 다음 구조로 설명된다.

```text
우리의 현재 API 실험: Python 프로그램이 OpenAI Responses API를 호출
친구의 AI 앱 실험:   ChatGPT/Claude 앱이 모델과 stdio MCP를 함께 사용
```

- 친구 방식은 저장소에 별도 `OPENAI_API_KEY`를 두고 모델 API를 호출하지 않는다.
- 이것이 ChatGPT 구독을 Python API 요청에 적용한 것이거나 API 결제 제한을 우회한 것은 아니다.
- 특정 친구 데스크톱 UI의 STDIO 지원이 사용자 계정·웹 UI·다른 호스트 버전에도 그대로 제공된다고 보장할 수 없다.
- 현재 우리 터널 설정 오류를 친구의 데스크톱 성공 사례만으로 해결됐다고 판단하지 않는다.

**우리도 stdio를 지원하는 데스크톱 호스트를 사용할 수 있다면, 기존 HTTP MCP를 호출하는 로컬 stdio 어댑터를 추가하는 선택지가 있다.** 현재 Python 서버가 이미 stdio로 등록 가능하게 구현되어 있다는 뜻은 아니며, 별도 구현·테스트가 필요하다. 그 경우에도 우리의 MCP_TOKEN 인증은 유지할 수 있다.

## 8. 수명 주기·동시성·실패 처리

### 8.1 앱 화면을 떠났을 때

| 항목 | 우리 | 친구 |
| --- | --- | --- |
| 소유자 | MainActivity의 CoroutineScope/Provider | BridgeService가 BridgeSession/reader/SDK 소유 |
| onStop | Bridge 취소, SDK 해제, 입력 토큰 제거 | UI 요청 취소·바인딩만 해제, 서비스 유지 |
| 종료 방법 | 화면 이탈 또는 Bridge 중지 | 알림 중지/화면의 AI 연결 종료 |
| 프로세스 종료 후 자동 복구 | 없음 | START_NOT_STICKY, 자동 복구 없음 |

친구의 Foreground Service 구조는 우리가 겪은 화면 전환 시 Bridge 중지·토큰 재입력 문제를 개선하는 데 참고할 수 있다. 다만 친구 보고서도 알림 중지/재진입 정리/장시간 유지의 모든 경계 사례를 검증 완료했다고 하지는 않는다.

근거: [BridgeService](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/app/src/main/java/com/example/pleostest/BridgeService.kt), [MainActivity](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/app/src/main/java/com/example/pleostest/MainActivity.kt), [BridgeSession](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/app/src/main/java/com/example/pleostest/bridge/BridgeSession.kt).

### 8.2 동시 요청

- 우리: 서버는 최대 16개 pending을 관리하지만 실제 Android SDK 조회는 Mutex로 한 번에 하나씩 진행한다.
- 친구: UI와 모든 AI 도구가 공통 reader 한 슬롯을 공유한다. 진행 중이면 새 조회를 BUSY로 거부한다.
- 친구 소켓 서버는 worker 2개이며, 슬롯이 없으면 추가 연결을 닫는 코드가 있다. PC 클라이언트는 네트워크 오류를 ANDROID_UNREACHABLE로 분류한다. 이 구조는 동시 부하에서 그 오류가 관측될 가능성을 설명하지만, **친구가 기록한 특정 오류의 확정 원인은 재현 없이 단정하지 않는다.**
- 친구 보고서에는 ChatGPT의 4개 동시 도구 호출에서 BUSY/ANDROID_UNREACHABLE, 3초 간격 순차 호출에서는 미재현이라고 적혀 있다.
- 우리의 16개·1,000회 성공은 빠른 Python mock_bridge 부하 결과다. 실제 NaviHelper/Android 16개 동시 호출을 보장하지 않는다.

### 8.3 오류 결과 계약

- 우리: 단일 내비 결과의 `status`를 사용한다. 업무 실패 status가 있어도 FastMCP가 반환한 일반 dict가 자동으로 `isError=true`가 되는 구조는 아니다.
- 친구: 항목별 상태를 보존하고 COMPLETE/PARTIAL/FAILED를 계산한다. MCP 출력에서 PARTIAL/FAILED에 `isError=true`를 명시한다.
- 친구는 SDK의 호출별 callback과 요청·stage 객체를 연결해 중복·늦은 전달을 검사한다.
- 우리 NaviHelper는 요청 ID 없는 공용 이벤트 리스너를 사용하므로 SDK 지연 이벤트의 요청 귀속에 별도 한계가 있다. Vehicle SDK의 요청별 callback과 동일한 조건이 아니다.

## 9. 인증과 로컬 연결의 차이

### 우리

- PC MCP/health용 `MCP_TOKEN`, Android Bridge용 `BRIDGE_TOKEN` 분리.
- 서버는 127.0.0.1에 바인딩.
- 현재 OAuth는 구현하지 않음. ChatGPT 터널 연결에는 runtime과 토큰 전달 설정이 추가로 필요.

### 친구

- Android 서버는 127.0.0.1에 바인딩하고 loopback 상대, 정확한 Host, Origin 부재를 검사.
- 인증 토큰을 사용하지 않는다. Node도 Authorization을 보내지 않는다.
- 같은 PC에서 같은 HTTP 요청 형식을 만들 수 있는 다른 로컬 프로세스를 구분하는 인증은 아니다.
- foreground 서비스가 켜지고 ADB forward가 유지되는 동안 이 로컬 접근 범위가 유지된다.

토큰 없는 로컬 연결은 입력·재연결 부담을 줄이는 대신 접근 통제의 범위가 다르다. **우리 연결을 간단하게 만들기 위해 토큰부터 제거해야 한다는 결론은 아니다.**

근거: [DoorBridgeProtocol.checkHead](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/app/src/main/java/com/example/pleostest/bridge/DoorBridgeProtocol.kt#L59).

## 10. 테스트와 검증 증거 비교

| 항목 | 우리 | 친구 |
| --- | --- | --- |
| Python 기능 테스트 | 12개 통과 이력 | 해당 언어 경로 없음 |
| Android JVM 테스트 | 18개 통과 이력 | 보고서상 87개 통과. 코드의 @Test 선언도 87개이며 기존 산술 1개 포함 |
| Node MCP 테스트 | 없음 | 보고서상 36개 통과. test 선언 36개 확인 |
| Lint | 우리 최종 빌드 오류/경고 0건 | 보고서상 오류 0·경고 5개 |
| SDK 사용자 검증 | 내비 목적지·23km·31분을 PC MCP에서 두 번 확인 | 문·창문·EV 값 변경과 AI 답변 일치 보고 |
| 실제 모델 사용 | API 잔액 오류 응답까지; GPT 답변 미검증 | POC-REPORT에 ChatGPT/Claude 도구 호출·답변 성공 보고 |
| 부하 성능 자료 | mock_bridge 1,000회 JSON 보존 | 동일한 형식/조건의 부하 결과는 확인하지 못함 |
| 복구·재시작·장시간 | 미검증/추가 필요 | 보고서에도 일부 미검증 명시 |

테스트 수는 도메인 수와 코드 규모가 다르므로 단순한 품질 순위로 사용하지 않는다. 친구 테스트와 실측 성공은 이번 리뷰에서 재실행하지 않았으며, 같은 머신·같은 SDK·같은 부하의 성능 비교도 하지 않았다.

우리 성능 참고값: mock Bridge 1,000/1,000회 정상, 16개 워커, 약 306.4회/초, p95 55.855ms. 친구의 실제 SDK 단일 슬롯 결과와 직접 비교해 어느 쪽이 빠르다고 결론 내릴 수 없다.

## 11. Android 빌드 환경 차이

| 항목 | 우리 | 친구 |
| --- | --- | --- |
| 앱 패키지 | example.vehiclemcp | com.example.pleostest |
| 프로젝트 모듈 위치 | android/app | app |
| AGP | 8.7.3 | 9.4.1 |
| Gradle Wrapper | 8.9 | 9.6.0 |
| JDK 실행 기준 | 우리 빌드 이력 21; JVM target 17 | daemon 설정 25; Java source/target 11 |
| Kotlin 설정 | Kotlin Android plugin 1.9.25 명시 | AGP 내장 Kotlin 사용; README는 KGP 2.2.10 확인 기록 |
| compile/target SDK | 34 / 34 | 37 / 37 |
| minSdk | 28 | 34 |
| Node 요구 | 없음 | package.json: Node >=24.15.0 |

AGP·Gradle·Kotlin 설정을 통째로 복사하면 같은 SDK 코드를 옮기는 작업보다 큰 변경이 된다. 필요한 모듈·인터페이스를 분리해 통합하는 편이 낫다.

## 12. 문서의 시점 차이

친구 저장소에는 서로 다른 작업 시점의 문서가 함께 있다.

- `POC-REPORT.md`: Foreground Service 구현과 두 AI 앱 사용자 검증, 최종 87/36 검사 보고를 포함.
- `SoC-report.md`: 명시적으로 중단 시점 기록이며 일부 이슈가 Todo/In Progress로 남아 있다고 적음.
- `README.md`: 최신 기능 설명과 구현 전 환경표가 함께 있고, 일부 문장은 실행 미검증 상태를 유지.
- `AGENTS.md`: 아직 Activity/주요 소스가 없다는 설명과 산술 테스트 1개라는 설명이 현 코드와 다름.

따라서 이 보고서는 **현재 커밋 코드로 구조를 확인하고 POC-REPORT의 사용자 결과를 별도 인용**했다. 과거 SoC의 상태를 최신 코드의 미구현으로 해석하지 않았다. Linear의 현재 상태는 조회하지 않았으므로 Done 여부를 독립적으로 확인했다고도 하지 않는다.

근거: [POC-REPORT](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/POC-REPORT.md), [과거 SoC 보고서](https://github.com/HyeeSeong/pleostest/blob/0d288c8aeab3b2fd08d09a257d894cbfeca793ca/SoC-report.md).

## 13. 우리에게 권하는 다음 순서

1. **친구의 실제 AI 앱 실행 환경 확인:** ChatGPT 데스크톱 제품·버전과 STDIO 메뉴를 확인. 현재 사용 중인 웹의 URL/터널 메뉴와 구분.
2. **원하면 우리용 stdio 어댑터 추가:** 기존 Python HTTP MCP/Android/NaviHelper를 재사용하고, 앱별 로컬 MCP 프로세스가 기존 서버를 호출하도록 설계. 아직 구현된 기능으로 기록하지 않음.
3. **Foreground Service 수명 주기 검토:** 토큰 입력과 앱 화면 유지 부담을 줄이되, 종료·SDK 해제·알림·재진입 회귀 검사를 함께 추가.
4. **추가 도메인 통합은 별도 작업:** 우리 내비 도구와 친구 문·창문·에너지 도구를 함께 제공하는 방식 검토. SDK 버전/권한, 요청 ID, 출력 계약, BUSY 정책을 맞춰야 함.
5. **현재 코드 공유 정리:** 우리 최신 Android/벤치마크/문서를 팀이 clone할 수 있는 코드 브랜치·PR로 정리할지 결정. 기존 artifact 브랜치에 코드 일부가 있다고 전체 프로젝트로 빌드하지 않음.

통합 후 가능한 기능 예시는 '목적지까지 남은 거리/시간과 EV 잔량을 함께 설명'이다. 현재 두 결과만으로 도착 시 배터리나 충전 필요 여부를 계산할 수 있다고 가정하지 않는다.

## 14. 요약

**친구 프로젝트는 여러 차량 상태와 데스크톱 AI 연결의 사용자 검증이 앞서 기록되어 있고, 우리 프로젝트는 내비게이션 SDK 조회와 인증된 HTTP MCP/모의 부하 측정의 근거가 있다.**

두 프로젝트는 서로 대체하는 동일 앱이라기보다 도메인이 다른 두 읽기 전용 도구 구현이다. 친구의 stdio·서비스 소유 구조를 참고하면서 우리 내비게이션 도구를 유지하는 방향이 현재 목표와 잘 맞는다.
