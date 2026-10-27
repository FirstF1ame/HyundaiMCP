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
fun interface NavigationProvider {
    suspend fun readSnapshot(): JSONObject
}

class VehicleBridgeLoop(
    private val baseUrl: String,
    private val token: String,
    private val provider: NavigationProvider,
) {
    private val http = OkHttpClient.Builder()
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(12, TimeUnit.SECONDS)
        .callTimeout(14, TimeUnit.SECONDS)
        .build()

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

    suspend fun run() {
        while (currentCoroutineContext().isActive) {
            try {
                val command = poll() ?: continue
                if (command.getString("tool") != "get_navigation_info") continue
                val result = try {
                    provider.readSnapshot()
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (_: Exception) {
                    unavailable("sdk_error")
                }
                post(command.getString("command_id"), result)
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: IOException) {
                delay(1000)
            }
        }
    }

    companion object {
        /** Use this until a real, verified NaviHelper adapter exists. Never invent ETA. */
        fun unavailable(status: String = "unsupported"): JSONObject = JSONObject()
            .put("source", "pleos_sdk")
            .put("status", status)
            .put("observed_at", Instant.now().toString())
    }
}
