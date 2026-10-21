package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test

class LanPairingTest {
    private class Api(val cookie: String?, val status: Int = 200, val failSession: Boolean = false) : LanPairingApi {
        val posts = mutableListOf<Triple<String, String, String>>()
        override fun session(): String? { if (failSession) throw java.io.IOException("offline"); return cookie }
        override fun post(path: String, body: String, cookie: String): Int { posts += Triple(path, body, cookie); return status }
    }

    @Test fun opensTheWindowWithTheLocalSession() {
        val api = Api("galaxy_session=abc")
        assertTrue(LanPairing.openWindow(api))
        assertEquals(listOf(Triple("/api/bluetooth/action", "{\"operation\":\"accept_pair\"}", "galaxy_session=abc")), api.posts)
    }

    @Test fun fallsBackToManualPairingWhenThereIsNoSessionOrComma() {
        val none = Api(null)
        assertFalse(LanPairing.openWindow(none)); assertTrue(none.posts.isEmpty())
        assertFalse(LanPairing.openWindow(Api("c", status = 409)))
        assertFalse(LanPairing.openWindow(Api("c", failSession = true)))
    }
}
