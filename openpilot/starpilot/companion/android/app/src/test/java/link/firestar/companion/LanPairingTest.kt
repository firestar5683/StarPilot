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

    @Test fun saysWhyTheWindowCouldNotBeOpened() {
        val none = Api(null)
        assertEquals("comma gave this phone no local Galaxy session", LanPairing.openWindow(none)); assertTrue(none.posts.isEmpty())
        assertEquals("comma answered HTTP 409 (busy)", LanPairing.openWindow(Api("c", 409, "{\"error\":\"x\",\"code\":\"busy\"}")))
        assertEquals("comma answered HTTP 503 (radio_unavailable)", LanPairing.openWindow(Api("c", 503, "{\"code\":\"radio_unavailable\"}")))
        assertEquals("comma answered HTTP 403", LanPairing.openWindow(Api("c", 403, "{\"error\":\"Remote Galaxy request denied\"}")))
        assertEquals("offline", LanPairing.openWindow(Api("c", failSession = true)))
    }
}
