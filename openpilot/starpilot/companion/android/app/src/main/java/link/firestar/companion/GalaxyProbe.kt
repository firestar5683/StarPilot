package link.firestar.companion

import android.net.Network
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** A short application-level acknowledgement before committing the UI to Wi-Fi. */
object GalaxyProbe {
    const val TIMEOUT_MS = 900
    const val AUTOMATIC_DISCOVERY_MS = 2500L
    private const val MAX_RESPONSE_BYTES = 1024

    fun accepts(status: Int, contentType: String?, authenticated: Boolean, localAccess: Boolean): Boolean =
        status == 200 && contentType?.substringBefore(';')?.trim()?.equals("application/json", ignoreCase = true) == true &&
            authenticated && localAccess

    fun reachable(network: Network, origin: String, cookie: String?, opened: (HttpURLConnection) -> Unit): Boolean {
        require(Networks.localOrigin(origin) == origin)
        val connection = network.openConnection(URL("$origin/api/auth/session")) as HttpURLConnection
        opened(connection)
        return try {
            connection.connectTimeout = TIMEOUT_MS
            connection.readTimeout = TIMEOUT_MS
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Connection", "close")
            if (!cookie.isNullOrBlank()) connection.setRequestProperty("Cookie", cookie)
            val status = connection.responseCode
            val input = if (status == 200) connection.inputStream else connection.errorStream ?: return false
            val output = java.io.ByteArrayOutputStream()
            input.use {
                val buffer = ByteArray(256)
                while (true) {
                    val count = it.read(buffer)
                    if (count < 0) break
                    if (output.size() + count > MAX_RESPONSE_BYTES) return false
                    output.write(buffer, 0, count)
                }
            }
            val value = JSONObject(output.toString(Charsets.UTF_8.name()))
            accepts(status, connection.contentType, value.optBoolean("authenticated"), value.optBoolean("localAccess"))
        } catch (_: Exception) {
            false
        } finally {
            connection.disconnect()
        }
    }
}
