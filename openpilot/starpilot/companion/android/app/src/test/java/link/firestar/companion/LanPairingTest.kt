package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test

class LanPairingTest {
    private class Api(val cookie: String?, val status: Int = 200, val body: String = "{}", val failSession: Boolean = false) : LanPairingApi {
        val posts = mutableListOf<Triple<String, String, String>>()
        override fun session(): String? { if (failSession) throw java.io.IOException("offline"); return cookie }
        override fun post(path: String, body: String, cookie: String): Pair<Int, String> { posts += Triple(path, body, cookie); return status to this.body }
    }

    @Test fun opensTheWindowWithTheLocalSession() {
        val api = Api("galaxy_session=abc")
        assertNull(LanPairing.openWindow(api))
        assertEquals(listOf(Triple("/api/bluetooth/action", "{\"operation\":\"accept_pair\"}", "galaxy_session=abc")), api.posts)
    }

    @Test fun retriesWhileCommaIsBusyThenSucceeds() {
        var busyAnswers = 2
        val pauses = mutableListOf<Long>()
        val api = object : LanPairingApi {
            override fun session(): String? = "c"
            override fun post(path: String, body: String, cookie: String): Pair<Int, String> =
                if (busyAnswers-- > 0) 409 to "{\"code\":\"busy\"}" else 200 to "{}"
        }
        assertNull(LanPairing.openWindow(api, pause = { pauses += it }))
        assertEquals(2, pauses.size)
    }

    @Test fun readsTheCodeFromCommasSpacedJson() {
        val pauses = mutableListOf<Long>()
        assertEquals("comma answered HTTP 409 (busy)", LanPairing.openWindow(Api("c", 409, "{\"error\": \"x\", \"code\": \"busy\"}"), pause = { pauses += it }))
        assertEquals(3, pauses.size)
    }

    @Test fun givesUpAfterTheLastBusyAnswerAndNeverRetriesOtherRefusals() {
        val pauses = mutableListOf<Long>()
        assertEquals("comma answered HTTP 409 (busy)", LanPairing.openWindow(Api("c", 409, "{\"code\":\"busy\"}"), pause = { pauses += it }))
        assertEquals(3, pauses.size)
        pauses.clear()
        assertEquals("comma answered HTTP 503 (radio_unavailable)", LanPairing.openWindow(Api("c", 503, "{\"code\":\"radio_unavailable\"}"), pause = { pauses += it }))
        assertTrue(pauses.isEmpty())
        assertEquals("comma gave this phone no local Galaxy session", LanPairing.openWindow(Api(null), pause = { pauses += it }))
        assertTrue(pauses.isEmpty())
    }

    private class ReadyApi(val answers: MutableList<CommaReadiness?>, val cookie: String? = "c") : LanPairingApi {
        var asked = 0
        override fun session(): String? = cookie
        override fun post(path: String, body: String, cookie: String): Pair<Int, String> = 200 to "{}"
        override fun readiness(cookie: String): CommaReadiness? = answers[minOf(asked++, answers.size - 1)]
    }
    private fun answer(ready: Boolean, code: String) = CommaReadiness(ready, code, "msg $code")

    @Test fun waitsOutBootAndBridgeStartThenProceeds() {
        val api = ReadyApi(mutableListOf(answer(false, "starting"), answer(false, "bridge_starting"), answer(true, "ready")))
        val waited = mutableListOf<String>()
        assertNull(LanPairing.waitUntilReady(api, onWait = { waited += it }, pause = {}))
        assertEquals(listOf("msg starting", "msg bridge_starting"), waited)
    }

    @Test fun stopsAtOnceForBlockersSomeoneMustFixAndGivesUpAfterTheWaitLimit() {
        val parked = ReadyApi(mutableListOf(answer(false, "park_required")))
        assertEquals("park_required", LanPairing.waitUntilReady(parked, pause = { fail("must not wait") })!!.code)
        assertEquals("bluetooth_off", LanPairing.waitUntilReady(ReadyApi(mutableListOf(answer(false, "bluetooth_off"))), pause = { fail("must not wait") })!!.code)
        val stuck = ReadyApi(mutableListOf(answer(false, "bridge_starting")))
        val pauses = mutableListOf<Long>()
        assertEquals("bridge_starting", LanPairing.waitUntilReady(stuck, maxWaitMs = 9000, stepMs = 3000, pause = { pauses += it })!!.code)
        assertEquals(3, pauses.size)
    }

    @Test fun anOlderCommaOrNoSessionNeverBlocksPairing() {
        assertNull(LanPairing.waitUntilReady(ReadyApi(mutableListOf(null)), pause = {}))
        assertNull(LanPairing.waitUntilReady(ReadyApi(mutableListOf(answer(false, "park_required")), cookie = null), pause = {}))
    }

    @Test fun saysWhyTheWindowCouldNotBeOpened() {
        val none = Api(null)
        assertEquals("comma gave this phone no local Galaxy session", LanPairing.openWindow(none)); assertTrue(none.posts.isEmpty())
        assertEquals("comma answered HTTP 409 (busy)", LanPairing.openWindow(Api("c", 409, "{\"error\":\"x\",\"code\":\"busy\"}")))
        assertEquals("comma answered HTTP 503 (radio_unavailable)", LanPairing.openWindow(Api("c", 503, "{\"code\":\"radio_unavailable\"}")))
        assertEquals("comma answered HTTP 403", LanPairing.openWindow(Api("c", 403, "{\"error\":\"Remote Galaxy request denied\"}")))
        assertEquals("offline", LanPairing.openWindow(Api("c", failSession = true)))
    }
}
