package link.firestar.companion

import android.net.Network
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** What opening comma's phone pairing window needs from the network; tests supply it in memory. */
interface LanPairingApi {
    /** Session cookie when comma accepts this phone's local Galaxy session, otherwise null. */
    fun session(): String?
    /** POST [body] to [path] with that session; returns the HTTP status and response body. */
    fun post(path: String, body: String, cookie: String): Pair<Int, String>
}

/**
 * When the phone already reaches comma over Wi-Fi/LAN it opens comma's two-minute pairing window itself, the same call
 * as Pair phone on Galaxy's Bluetooth page, so nobody has to touch comma before the Bluetooth key claim.
 */
object LanPairing {
    const val WINDOW_PATH = "/api/bluetooth/action"
    const val WINDOW_BODY = "{\"operation\":\"accept_pair\"}"

    /** Null when the window opened, otherwise why not, in words fit for the pairing screen. */
    fun openWindow(api: LanPairingApi): String? = try {
        val cookie = api.session()
        if (cookie == null) "comma gave this phone no local Galaxy session"
        else {
            val (status, body) = api.post(WINDOW_PATH, WINDOW_BODY, cookie)
            if (status == 200) null else "comma answered HTTP $status${Regex("\"code\":\"([a-z_]+)\"").find(body)?.let { " (${it.groupValues[1]})" }.orEmpty()}"
        }
    } catch (e: Exception) { e.message ?: e.javaClass.simpleName }

    fun openWindow(network: Network, origin: String): String? = openWindow(object : LanPairingApi {
        override fun session(): String? {
            val connection = open(network, origin, "/api/auth/session", "")
            try {
                if (connection.responseCode != 200) return null
                val json = JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
                if (!json.optBoolean("authenticated") || !json.optBoolean("localAccess")) return null
                return connection.getHeaderField("Set-Cookie")?.substringBefore(';')?.ifEmpty { null }
            } finally { connection.disconnect() }
        }

        override fun post(path: String, body: String, cookie: String): Pair<Int, String> {
            val connection = open(network, origin, path, cookie)
            try {
                connection.requestMethod = "POST"; connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toByteArray()) }
                val status = connection.responseCode
                val stream = if (status in 200..299) connection.inputStream else connection.errorStream
                return status to (stream?.bufferedReader()?.use { it.readText() } ?: "")
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
