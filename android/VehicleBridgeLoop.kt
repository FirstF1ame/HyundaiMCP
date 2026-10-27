package example.vehiclemcp

import java.io.IOException
import java.time.Instant
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

/**
 * Android integration template, NOT a complete APK or a NaviHelper implementation.
 * Add to an existing Pleos application with OkHttp and kotlinx-coroutines-android.
 * Start from a foreground UI-owned CoroutineScope and cancel when the UI stops.
 * provider must return fresh SDK data and handle SDK callbacks on the required dispatcher.
 */
// 실제 NaviHelper 콜백을 응답 JSON으로 변환하는 어댑터 경계. 현재는 인터페이스만 정의한다.
fun interface NavigationProvider {
    suspend fun readSnapshot(): JSONObject
}

// baseUrl: 로컬 서버 주소 / token: Bridge 전용 토큰 / provider: SDK 조회 구현체.
class VehicleBridgeLoop(
    private val baseUrl: String,
    private val token: String,
    private val provider: NavigationProvider,
) {
    // 서버의 10초 long polling보다 긴 읽기 제한을 두되 통신은 무한정 기다리지 않는다.
    private val http = OkHttpClient.Builder()
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(12, TimeUnit.SECONDS)
        .callTimeout(14, TimeUnit.SECONDS)
        .build()

    // 블로킹 OkHttp 호출을 IO 디스패처에서 수행한다. 204는 오류가 아닌 명령 없음이다.
    private suspend fun poll(): JSONObject? = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("$baseUrl/bridge/commands")
            .header("Authorization", "Bearer $token").build()
        http.newCall(request).execute().use { response ->
            when {
                response.code == 204 -> null
                response.isSuccessful -> JSONObject(response.body!!.string())
                else -> throw IOException("Bridge poll HTTP ${response.code}")
            }
        }
    }

    // 원래 명령 ID와 조회 결과를 함께 반환한다. 409는 이미 만료/완료된 요청이므로 무시한다.
    private suspend fun post(id: String, result: JSONObject) = withContext(Dispatchers.IO) {
        val body = JSONObject().put("command_id", id).put("result", result).toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder().url("$baseUrl/bridge/results")
            .header("Authorization", "Bearer $token").post(body).build()
        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful && response.code != 409) {
                throw IOException("Bridge result HTTP ${response.code}")
            }
        }
    }

    // 화면 소유 CoroutineScope에서 실행하고 화면 종료 시 취소해야 한다.
    suspend fun run() {
        while (currentCoroutineContext().isActive) {
            try {
                val command = poll() ?: continue
                if (command.getString("tool") != "get_navigation_info") continue
                // 실제 데이터 조회 책임은 provider에 있다. SDK 예외를 임의의 거리/시간으로 대체하지 않는다.
                val result = try {
                    provider.readSnapshot()
                } catch (cancelled: CancellationException) {
                    // 취소는 오류 응답으로 바꾸지 않고 전파해 화면 종료 시 루프도 끝나게 한다.
                    throw cancelled
                } catch (_: Exception) {
                    unavailable("sdk_error")
                }
                post(command.getString("command_id"), result)
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: IOException) {
                // 네트워크 실패 후 1초 쉬어 즉시 재시도하는 과도한 루프를 피한다.
                delay(1000)
            }
        }
    }

    companion object {
        /** Use this until a real, verified NaviHelper adapter exists. Never invent ETA. */
        // 실패/미지원 응답에는 목적지·거리·시간을 넣지 않는다. source는 실제 연결 증명이 아니다.
        fun unavailable(status: String = "unsupported"): JSONObject = JSONObject()
            .put("source", "pleos_sdk")
            .put("status", status)
            .put("observed_at", Instant.now().toString())
    }
}
