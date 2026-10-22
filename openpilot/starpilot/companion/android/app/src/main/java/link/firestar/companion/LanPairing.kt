package link.firestar.companion

import android.net.Network
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Whether comma can take a phone's Bluetooth pairing right now, from its /api/companion/bluetooth-ready. */
data class CommaReadiness(val ready: Boolean, val code: String, val message: String)

/** What opening comma's phone pairing window needs from the network; tests supply it in memory. */
interface LanPairingApi {
    /** comma's answer to "are you ready to pair?", or null from an older comma that cannot say. */
    fun readiness(cookie: String): CommaReadiness? = null
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
    const val READY_PATH = "/api/companion/bluetooth-ready"
    private val WAITABLE = setOf("starting", "bridge_starting")
    const val WINDOW_PATH = "/api/bluetooth/action"
    const val WINDOW_BODY = "{\"operation\":\"accept_pair\"}"

    /**
     * Null when comma is ready to pair (or is too old to say), otherwise why not. Short-lived states, such as comma
     * just booting or its Bluetooth bridge starting, are waited out for up to [maxWaitMs]; the rest need someone at comma.
     */
    fun waitUntilReady(api: LanPairingApi, maxWaitMs: Long = 45000, stepMs: Long = 3000,
                       onWait: (String) -> Unit = {}, pause: (Long) -> Unit = { Thread.sleep(it) }): CommaReadiness? {
        val cookie = runCatching { api.session() }.getOrNull() ?: return null
        var waited = 0L
        while (true) {
            val answer = runCatching { api.readiness(cookie) }.getOrNull() ?: return null
            if (answer.ready) return null
            if (answer.code !in WAITABLE || waited >= maxWaitMs) return answer
            onWait(answer.message)
            pause(stepMs); waited += stepMs
        }
    }

    fun waitUntilReady(network: Network, origin: String, onWait: (String) -> Unit = {}): CommaReadiness? =
        waitUntilReady(realApi(network, origin), onWait = onWait)

    /**
     * Null when the window opened, otherwise why not, in words fit for the pairing screen. comma answers 409 busy while
     * Android Auto or Bluetooth is still settling (for example just after a reboot), so that one answer is retried a few times.
     */
    fun openWindow(api: LanPairingApi, attempts: Int = 4, pause: (Long) -> Unit = { Thread.sleep(it) }): String? {
        var reason: String? = null
        for (attempt in 1..attempts) {
            val (why, busy) = once(api)
            reason = why
            if (why == null || !busy || attempt == attempts) break
            pause(2500)
        }
        return reason
    }

    private fun once(api: LanPairingApi): Pair<String?, Boolean> = try {
        val cookie = api.session()
        if (cookie == null) "comma gave this phone no local Galaxy session" to false
        else {
            val (status, body) = api.post(WINDOW_PATH, WINDOW_BODY, cookie)
            val code = Regex("\"code\"\\s*:\\s*\"([a-z_]+)\"").find(body)?.groupValues?.get(1)
            if (status == 200) null to false
            else "comma answered HTTP $status${code?.let { " ($it)" }.orEmpty()}" to (status == 409 && code == "busy")
        }
    } catch (e: Exception) { (e.message ?: e.javaClass.simpleName) to false }

    fun openWindow(network: Network, origin: String): String? = openWindow(realApi(network, origin))

    private fun realApi(network: Network, origin: String) = object : LanPairingApi {
        override fun readiness(cookie: String): CommaReadiness? {
            val connection = open(network, origin, READY_PATH, cookie)
            try {
                if (connection.responseCode != 200) return null
                val json = JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
                if (json.optInt("schema") != 1 || !json.has("ready")) return null
                return CommaReadiness(json.getBoolean("ready"), json.optString("code"), json.optString("message"))
            } finally { connection.disconnect() }
        }

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
    }

    private fun open(network: Network, origin: String, path: String, cookie: String) =
        (network.openConnection(URL(origin + path)) as HttpURLConnection).apply {
            connectTimeout = 3000; readTimeout = 3000; instanceFollowRedirects = false
            setRequestProperty("Origin", origin)
            if (cookie.isNotEmpty()) setRequestProperty("Cookie", cookie)
        }
}
