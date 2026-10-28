package example.vehiclemcp

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeout

/**
 * 목적지 요청과 SDK 콜백을 연결하는 조회 상태 머신.
 * Provider가 호출/콜백을 Main 디스패처로 모으므로 pending은 한 스레드에서 접근한다.
 * isRouting=false만으로 목적지가 없다고 단정하지 않고 목적지 API 응답을 기다린다.
 */
class NavigationQuery(
    private val requestDestination: () -> Unit,
    private val requestRouteState: () -> Unit,
    private val report: (String) -> Unit = {},
    private val timeoutMillis: Long = 6_000,
) {
    private val mutex = Mutex()
    private var pending: CompletableDeferred<NavigationResult>? = null

    suspend fun read(): NavigationResult = mutex.withLock {
        val reply = CompletableDeferred<NavigationResult>()
        pending = reply
        try {
            withTimeout(timeoutMillis) {
                report("목적지 SDK 응답 대기 중…")
                requestDestination()
                // 진단 정보 수신 여부가 목적지 조회를 막지 않게 한다.
                try {
                    requestRouteState()
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (_: Exception) {
                    report("경로 상태 진단 요청 실패 · 목적지 응답은 계속 대기합니다")
                }
                reply.await()
            }
        } catch (_: TimeoutCancellationException) {
            report("목적지 콜백 미수신 · 목적지 없음으로 확정할 수 없습니다")
            NavigationResult("sdk_error")
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (error: Exception) {
            report("SDK 조회 요청 실패 (${error.javaClass.simpleName})")
            NavigationResult("sdk_error")
        } finally {
            pending = null
            reply.cancel()
        }
    }

    fun onRouteState(isRouting: Boolean, mode: String) {
        // 값은 보여 주되 결과 판정의 gate로 사용하지 않는다.
        report("SDK 경로 상태 · isRouting=$isRouting · mode=$mode")
    }

    fun onDestination(result: NavigationResult) {
        if (pending?.complete(result) == true) report("목적지 콜백 수신 완료")
    }

    fun onRouteCancelled() {
        // 현재 조회 중 명시적인 경로 취소 이벤트가 도착한 경우에만 이 상태를 만든다.
        if (pending?.complete(NavigationResult("no_destination")) == true) {
            report("경로 취소 이벤트 수신 · 활성 조회 종료")
        }
    }

    fun onDestinationChanged() {
        // 변경 도중의 목적지와 이전 거리/시간을 혼합하지 않는다.
        if (pending?.complete(NavigationResult("sdk_error")) == true) {
            report("조회 중 목적지 변경 · 다시 조회하세요")
        }
    }

    fun onError(code: String) {
        pending?.complete(NavigationResult("sdk_error"))
        report("SDK 오류 이벤트 · code=$code")
    }

    fun close() {
        pending?.cancel()
        pending = null
    }
}
