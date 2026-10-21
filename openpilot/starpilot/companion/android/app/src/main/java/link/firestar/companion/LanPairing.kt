package link.firestar.companion

import android.net.Network
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** What opening comma's phone pairing window needs from the network; tests supply it in memory. */
interface LanPairingApi {
    /** Session cookie when comma accepts this phone's local Galaxy session, otherwise null. */
    fun session(): String?
    /** POST [body] to [path] with that session; returns the HTTP status. */
    fun post(path: String, body: String, cookie: String): Int
}

/**
 * When the phone already reaches comma over Wi-Fi/LAN it opens comma's two-minute pairing window itself, the same call
 * as Pair phone on Galaxy's Bluetooth page, so nobody has to touch comma before the Bluetooth key claim.
 */
object LanPairing {
    const val WINDOW_PATH = "/api/bluetooth/action"
    const val WINDOW_BODY = "{\"operation\":\"accept_pair\"}"

    fun openWindow(api: LanPairingApi): Boolean = runCatching {
        val cookie = api.session() ?: return false
        api.post(WINDOW_PATH, WINDOW_BODY, cookie) == 200
    }.getOrDefault(false)

    fun openWindow(network: Network, origin: String): Boolean = openWindow(object : LanPairingApi {
        override fun session(): String? {
            val connection = open(network, origin, "/api/auth/session", "")
            try {
                if (connection.responseCode != 200) return null
                val json = JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
                if (!json.optBoolean("authenticated") || !json.optBoolean("localAccess")) return null
                return connection.getHeaderField("Set-Cookie")?.substringBefore(';')?.ifEmpty { null }
            } finally { connection.disconnect() }
        }

        override fun post(path: String, body: String, cookie: String): Int {
            val connection = open(network, origin, path, cookie)
            try {
                connection.requestMethod = "POST"; connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toByteArray()) }
                return connection.responseCode
            } finally { connection.disconnect() }
        }
    })

    private fun open(network: Network, origin: String, path: String, cookie: String) =
        (network.openConnection(URL(origin + path)) as HttpURLConnection).apply {
            connectTimeout = 3000; readTimeout = 3000; instanceFollowRedirects = false
            setRequestProperty("Origin", origin)
            if (cookie.isNotEmpty()) setRequestProperty("Cookie", cookie)
        }
}
