# MCP local benchmark (Windows PowerShell)

AVD/Pleos Navigation/GPT API 없이 mock과 Python Bridge 시뮬레이터를 비교합니다.
스크립트는 기존 source ZIP의 Python 코드 및 고정 모의 값(12300 m, 1080 s)에 맞춰져 있습니다.
이 브랜치의 benchmark_mcp.py를 로컬 저장소의 scripts/benchmark_mcp.py에 저장하세요.
모든 명령은 pyproject.toml과 .env가 있는 HyundaiMCP 최상위 폴더에서 실행합니다.

## 1. 기능 기준 확인

```
.\.venv\Scripts\python.exe -m pytest -q
```

현재 기준 12 passed. .env는 기존 파일을 그대로 사용하세요.

## 2. mock 기준 측정

터미널 A:
```
$env:VEHICLE_MODE = "mock"
.\.venv\Scripts\python.exe -m vehicle_mcp.server
```

터미널 B:
```
.\.venv\Scripts\python.exe scripts/benchmark_mcp.py --requests 100 --concurrency 1 --expected-source mock --label mock-c1 --output benchmark-results/mock-c1.json
```

## 3. Bridge 측정

A에서 Ctrl+C로 자신이 실행한 서버를 중지한 뒤:
```
$env:VEHICLE_MODE = "bridge"
.\.venv\Scripts\python.exe -m vehicle_mcp.server
```

터미널 B:
```
$env:VEHICLE_MODE = "bridge"
.\.venv\Scripts\python.exe scripts/mock_bridge.py
```

터미널 C:
```
.\.venv\Scripts\python.exe scripts/benchmark_mcp.py --requests 100 --concurrency 1 --expected-source mock_bridge --label bridge-c1 --output benchmark-results/bridge-c1.json
```

Android 앱의 Bridge나 다른 시뮬레이터를 동시에 연결하지 마세요.
서버 포트 점유 오류가 나면 이전에 실행한 서버를 확인하세요. 타인의 프로세스는 중지하지 마세요.

## 4. 동시 부하

A와 B는 그대로 두고 C에서:
```
foreach ($c in 4, 8, 16) {
    .\.venv\Scripts\python.exe scripts/benchmark_mcp.py --requests 100 --concurrency $c --expected-source mock_bridge --label "bridge-c$c" --output "benchmark-results/bridge-c$c.json"
    if ($LASTEXITCODE -ne 0) { break }
}
```

mock 동시 부하도 비교하려면 B의 시뮬레이터를 Ctrl+C로 종료하고, A 서버를 mock으로 재시작한 뒤
위 명령의 expected-source를 mock으로 바꾸고 label/output 이름도 mock으로 바꾸세요.
각 파일의 samples가 실제 요청별 상태와 시간을 보존합니다.

## 5. 장애 및 결과 매칭

C에서:
```
.\.venv\Scripts\python.exe -m pytest -q tests/test_mcp.py -k "timeout or offline or round_trip or concurrent"
```

기존 테스트가 독립 임시 HTTP 서버로 오프라인, 시간 초과, 오래된/미래 데이터,
오류 상태, 중복 응답, 역순 응답의 요청 ID 매칭을 검증합니다.
이 선택 실행은 정상 호출 지연 측정과 구분합니다. 임의 지터/응답 손실률의 부하 주입은 이 스크립트에 없습니다.

## 6. 결과 해석 및 반복

- status_counts: 정상 모의 호출은 모두 ok여야 합니다. busy/timeout/exception은 별도로 조사합니다.
- success_rate: 1.0이면 모든 측정 호출 성공. 단위는 비율(0..1)입니다.
- successful_call_latency_ms: 세션 초기화와 워밍업을 제외한 성공 호출 p50/p95/p99(밀리초).
- all_call_latency_ms: 실패도 포함한 전체 호출 지연. 실패가 많은데 성공 지연만 비교하지 마세요.
- session_initialization_ms: 세션별 초기화 시간. 각 세션은 list_tools와 warmup을 완료한 뒤 부하를 시작합니다.
- successful_requests_per_second: 측정 구간의 성공 처리량. 100개 요청은 전체 합계이며 워커당 100개가 아닙니다.

mock과 Bridge는 같은 동시성/장비/요청 수에서 비교하고 각각 3회 이상 반복하세요.
재실행 시 output 파일명을 바꾸세요. 기존 보고서는 덮어쓰지 않습니다.
초기 100회는 점검용입니다. p99 안정성을 보려면 --requests 1000 등 더 많은 표본을 사용하세요.

요청은 워커당 순차 호출하는 closed-loop 방식입니다. 일정 초당 유입률을 보장하는 테스트가 아닙니다.
SDK 응답 속도, 실제 차량 데이터 정확도, GPT 자연어 품질은 이 결과로 검증되지 않습니다.

## 7. 장시간 점검

정상 단기 측정 이후 Bridge 동시성 4 / 100회 실행을 5초 쉬며 120회 반복하는 예입니다.
10분 이상 실행되며 컴퓨터 성능에 따라 더 길어집니다. 중단은 Ctrl+C.

```
for ($i = 1; $i -le 120; $i++) {
    .\.venv\Scripts\python.exe scripts/benchmark_mcp.py --requests 100 --concurrency 4 --expected-source mock_bridge --label "soak-$i" --output "benchmark-results/soak-$i.json"
    if ($LASTEXITCODE -ne 0) { break }
    Start-Sleep -Seconds 5
}
```

각 묶음은 새 MCP 세션을 만듭니다. 서버/Bridge는 유지되어 누적 오류와 지연 추세를 확인할 수 있습니다.
단일 세션의 장기 유지나 자동 메모리 누수 검사는 아닙니다. 작업 관리자에서 서버 프로세스의
메모리도 관찰하되 단순 증가만으로 누수라고 결론 내리지 마세요.
정리가 끝나면 A/B의 자신이 실행한 서버와 시뮬레이터를 Ctrl+C로 중지합니다.
