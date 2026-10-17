package link.firestar.companion

import android.net.Network
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Small Galaxy client for requests made from the app itself over Wi-Fi, outside the web view. */
class GalaxyWifi(private val network: Network, private val origin: String) {
    private var cookie: String? = null

    private fun connection(path: String) = (network.openConnection(URL(origin + path)) as HttpURLConnection).apply {
        instanceFollowRedirects = false; connectTimeout = 5000; readTimeout = 8000
        setRequestProperty("Origin", origin)
    }

    private fun session(): String {
        cookie?.let { return it }
        val call = connection("/api/auth/session")
        try {
            check(call.responseCode == 200) { "Galaxy authentication failed" }
            return (call.getHeaderField("Set-Cookie")?.substringBefore(';') ?: error("Galaxy session unavailable")).also { cookie = it }
        } finally { call.disconnect() }
    }

    fun request(method: String, path: String, payload: JSONObject? = null): Pair<Int, JSONObject> {
        val call = connection(path)
        try {
            call.requestMethod = method
            call.setRequestProperty("Cookie", session())
            if (payload != null) {
                call.doOutput = true
                call.setRequestProperty("Content-Type", "application/json")
                call.outputStream.use { it.write(payload.toString().toByteArray()) }
            }
            val status = call.responseCode
            val body = (if (status in 200..299) call.inputStream else call.errorStream)?.use { input ->
                val bytes = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(1024)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    require(bytes.size() + count <= 65536) { "Galaxy response too large" }
                    bytes.write(buffer, 0, count)
                }
                bytes.toByteArray()
            } ?: ByteArray(0)
            return status to (if (body.isEmpty()) JSONObject() else JSONObject(String(body)))
        } finally { call.disconnect() }
    }

    fun bluetoothStatus(): AudioPairing.Snapshot? {
        val (status, value) = request("GET", "/api/bluetooth/status")
        if (status != 200) return null
        // Only the window this phone opened counts; any other pairing belongs to someone else.
        val pairing = value.optJSONObject("pairing")?.takeIf { it.optBoolean("incoming") }
        val prompt = pairing?.optJSONObject("prompt")?.let {
            AudioPairing.Prompt(it.optString("id"), it.optString("kind"), it.optString("value"), it.optBoolean("displayOnly"))
        }
        return AudioPairing.Snapshot(value.optString("adapterAddress"), value.optString("adapterName"), pairing?.optString("state"), prompt)
    }

    fun openAudioWindow(): AudioPairing.Open =
        when (request("POST", "/api/bluetooth/action", JSONObject().put("operation", "accept_pair")).first) {
            200 -> AudioPairing.Open.OPENED
            400 -> AudioPairing.Open.UNSUPPORTED  // older comma rejects the unknown operation
            409 -> AudioPairing.Open.BUSY
            else -> AudioPairing.Open.FAILED
        }

    fun respond(promptId: String, accepted: Boolean): Boolean =
        request("POST", "/api/bluetooth/action", JSONObject().put("operation", "pairing_response")
            .put("promptId", promptId).put("accepted", accepted)).first == 200
}
