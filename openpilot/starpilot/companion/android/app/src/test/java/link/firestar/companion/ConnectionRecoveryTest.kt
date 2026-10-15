package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test

class ConnectionRecoveryTest {
    @Test fun interruptedSearchResumesOnceAfterWifiSettings() {
        val events = mutableListOf<String>()
        val recovery = ConnectionRecovery({ events.add("search:$it") }, { events.add("connect") }, { events.add("stop") })
        recovery.resumed() // Initial onResume after onCreate must not duplicate its connection attempt.
        assertTrue(events.isEmpty())
        recovery.stopped(searchAutomatic = true, disconnected = true)
        assertEquals(listOf("stop"), events)
        recovery.resumed()
        recovery.resumed()
        assertEquals(listOf("stop", "search:true"), events)
    }

    @Test fun disconnectedScreenReconnectsAfterJoiningWifi() {
        val events = mutableListOf<String>()
        val recovery = ConnectionRecovery({ events.add("search:$it") }, { events.add("connect") }, { events.add("stop") })
        recovery.stopped(searchAutomatic = null, disconnected = true)
        recovery.resumed()
        assertEquals(listOf("stop", "connect"), events)
    }

    @Test fun manualSearchRetainsItsModeAndConnectedScreenStaysConnected() {
        val events = mutableListOf<String>()
        val recovery = ConnectionRecovery({ events.add("search:$it") }, { events.add("connect") }, { events.add("stop") })
        recovery.stopped(searchAutomatic = false, disconnected = false)
        recovery.resumed()
        assertEquals(listOf("stop", "search:false"), events)
        events.clear()
        recovery.stopped(searchAutomatic = null, disconnected = false)
        recovery.resumed()
        assertEquals(listOf("stop"), events)
    }
}
