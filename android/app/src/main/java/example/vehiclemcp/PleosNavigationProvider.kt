package example.vehiclemcp

import ai.pleos.playground.navi.constants.NaviErrorCode
import ai.pleos.playground.navi.constants.NavigationStatus
import ai.pleos.playground.navi.data.DestinationInfo
import ai.pleos.playground.navi.data.RouteStateInfo
import ai.pleos.playground.navi.helper.NaviHelper
import ai.pleos.playground.navi.helper.listener.NaviHelperEventListener
import android.content.Context
import kotlinx.coroutines.*
import org.json.JSONObject

/**
 * NaviHelper 3.0.5 공식 공개 API를 사용하는 어댑터.
 * SDK에는 요청 ID가 없으므로 조회를 직렬화하고 콜백 수신 시각을 보존한다.
 */
class PleosNavigationProvider(context: Context, private val report: (String) -> Unit) : NavigationProvider {
    private val helper = NaviHelper(context.applicationContext)
    private val callbacks = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var connected = false
    private var closed = false
    private val query = NavigationQuery(
        requestDestination = { helper.getDestinationInfo() },
        requestRouteState = { helper.getRouteStateInfo() },
        report = report,
    )

    private val listener = object : NaviHelperEventListener {
        override fun onRouteStateInfo(routeStateInfo: RouteStateInfo) {
            callbacks.launch { query.onRouteState(routeStateInfo.isRouting, routeStateInfo.naviMode.name) }
        }
        override fun onDestinationInfo(destinationInfo: DestinationInfo) {
            // SDK 명세: name=목적지, remainDistance=미터, remainTime=초.
            val result = NavigationResult("ok", name = destinationInfo.name,
                distanceMeters = destinationInfo.remainDistance, durationSeconds = destinationInfo.remainTime)
            callbacks.launch { query.onDestination(result) }
        }
        override fun onRouteCancelled() {
            callbacks.launch { query.onRouteCancelled() }
        }
        override fun onDestinationChanged() {
            callbacks.launch { query.onDestinationChanged() }
        }
        override fun onNavigationStatus(status: NavigationStatus) {
            // 단독 상태 이벤트로 목적지 유무를 확정하지 않는다. API 결과와 대조할 진단이다.
            callbacks.launch { report("SDK 내비게이션 상태 · ${status.name}") }
        }
        override fun onError(errorCode: NaviErrorCode) {
            // 원문 데이터 대신 SDK enum 코드만 화면에 표시한다.
            callbacks.launch { query.onError(errorCode.name) }
        }
    }

    fun start() {
        report("NaviHelper 연결 중…")
        try {
            helper.initialize(onConnected = {
                callbacks.launch {
                    if (!closed) {
                        connected = true
                        helper.addListener(listener)
                        report("NaviHelper 연결됨 · 목적지 조회 가능")
                    }
                }
            }, onFailed = {
                callbacks.launch { connected = false; report("SDK 연결 실패 · Pleos Navi Service 실행을 확인하세요") }
            })
        } catch (_: Exception) {
            report("SDK 초기화 실패 · SDK 서비스/권한을 확인하세요")
        }
    }

    override suspend fun readSnapshot(): JSONObject = withContext(Dispatchers.Main.immediate) {
        if (!connected || closed) {
            report("SDK 미연결 · 연결 후 다시 조회하세요")
            NavigationResult("sdk_error").toJson()
        } else {
            query.read().toJson()
        }
    }

    fun close() {
        closed = true
        connected = false
        callbacks.cancel()
        query.close()
        runCatching { helper.removeListener(listener) }
        runCatching { helper.release() }
    }
}
