package example.vehiclemcp

import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Test

/** SDK의 콜백 순서/미응답을 제어해 실제 조회 상태 머신의 행동을 검증한다. */
@OptIn(ExperimentalCoroutinesApi::class)
class NavigationQueryTest {
    private fun destination(name: String = "테스트 목적지", distance: Int = 23000) =
        NavigationResult("ok", name = name, distanceMeters = distance, durationSeconds = 2040)

    @Test fun falseIsRoutingStillRequestsAndAcceptsDestination() = runTest {
        var requested = 0
        val query = NavigationQuery({ requested++ }, {})
        val read = async { query.read() }
        runCurrent()
        assertEquals(1, requested)
        query.onRouteState(false, "ROUTE_GUIDING")
        runCurrent()
        assertFalse("isRouting=false must not terminate the destination query", read.isCompleted)
        query.onDestination(destination())
        val result = read.await().toJson()
        assertEquals("ok", result.getString("status"))
        assertEquals("테스트 목적지", result.getString("destination_name"))
        assertEquals(23000, result.getInt("remaining_distance_m"))
    }

    @Test fun missingRouteStateCallbackDoesNotBlockDestination() = runTest {
        val query = NavigationQuery({}, {})
        val read = async { query.read() }
        runCurrent()
        query.onDestination(destination())
        assertEquals("ok", read.await().status)
    }

    @Test fun diagnosticRequestFailureDoesNotDiscardDestination() = runTest {
        val query = NavigationQuery({}, { throw IllegalStateException("diagnostic unavailable") })
        val read = async { query.read() }
        runCurrent()
        query.onDestination(destination())
        assertEquals("ok", read.await().status)
    }

    @Test fun absentDestinationCallbackIsUnknownErrorNotNoDestination() = runTest {
        val query = NavigationQuery({}, {}, timeoutMillis = 100)
        val read = async { query.read() }
        runCurrent()
        query.onRouteState(false, "SAFE_GUIDING")
        advanceTimeBy(101)
        val result = read.await().toJson()
        assertEquals("sdk_error", result.getString("status"))
        assertFalse(result.has("destination_name"))
        assertFalse(result.has("remaining_distance_m"))
    }

    @Test fun explicitCancellationEventReturnsNoDestinationWithoutNumbers() = runTest {
        val query = NavigationQuery({}, {})
        val read = async { query.read() }
        runCurrent()
        query.onRouteCancelled()
        val result = read.await().toJson()
        assertEquals("no_destination", result.getString("status"))
        assertFalse(result.has("remaining_duration_s"))
    }

    @Test fun sdkErrorDoesNotBecomeNoDestinationOrInventValues() = runTest {
        val query = NavigationQuery({}, {})
        val read = async { query.read() }
        runCurrent()
        query.onError("CAUSE_SEARCH_ROUTE")
        val result = read.await().toJson()
        assertEquals("sdk_error", result.getString("status"))
        assertFalse(result.has("remaining_distance_m"))
    }

    @Test fun destinationChangeDuringQueryRequiresRetry() = runTest {
        val query = NavigationQuery({}, {})
        val read = async { query.read() }
        runCurrent()
        query.onDestinationChanged()
        query.onDestination(destination())
        assertEquals("sdk_error", read.await().status)
    }

    @Test fun callbackBeforeQueryIsNotReusedAsFreshResult() = runTest {
        val query = NavigationQuery({}, {}, timeoutMillis = 100)
        query.onDestination(destination("old"))
        val read = async { query.read() }
        advanceUntilIdle()
        assertEquals("sdk_error", read.await().status)
    }

    @Test fun concurrentQueriesSerializeAndKeepTheirOwnResults() = runTest {
        var requested = 0
        val query = NavigationQuery({ requested++ }, {})
        val first = async { query.read() }
        val second = async { query.read() }
        runCurrent()
        assertEquals(1, requested)
        query.onDestination(destination("first", 111))
        runCurrent()
        assertEquals(2, requested)
        assertFalse(second.isCompleted)
        query.onDestination(destination("second", 222))
        assertEquals(111, first.await().distanceMeters)
        assertEquals(222, second.await().distanceMeters)
    }

    @Test fun callerCancellationDoesNotTurnIntoSuccessAndAllowsNextQuery() = runTest {
        val query = NavigationQuery({}, {})
        val first = async { query.read() }
        runCurrent()
        first.cancelAndJoin()
        assertTrue(first.isCancelled)
        // 취소 후 다음 요청 전에 도착한 지연 이벤트는 재사용하지 않는다.
        query.onDestination(destination("old"))
        val second = async { query.read() }
        runCurrent()
        assertFalse(second.isCompleted)
        query.onDestination(destination("fresh"))
        assertEquals("fresh", second.await().name)
    }

    @Test fun permissionExceptionProducesSdkError() = runTest {
        val query = NavigationQuery({ throw SecurityException("denied") }, {})
        assertEquals("sdk_error", query.read().status)
    }

    @Test fun providerShutdownCancelsActiveQuery() = runTest {
        val query = NavigationQuery({}, {})
        val read = async { query.read() }
        runCurrent()
        query.close()
        runCurrent()
        assertTrue(read.isCancelled)
    }
}
