package link.firestar.companion

import android.app.Activity
import android.content.Intent
import android.net.*
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.TextView
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.atomic.AtomicBoolean

class ShareActivity : Activity() {
    private val done = AtomicBoolean(false)
    private val handler = Handler(Looper.getMainLooper())
    private var callback: ConnectivityManager.NetworkCallback? = null
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        setContentView(TextView(this).apply { text = "Opening destination in Galaxy…"; setPadding(40, 100, 40, 40) })
        val text = (intent.getStringExtra(Intent.EXTRA_TEXT) ?: intent.dataString ?: "").take(8192)
        val short = Regex("https://(?:maps\\.app\\.goo\\.gl|goo\\.gl/maps)/[^\\s]+").find(text)?.value
        if (short == null) { complete(text); return }
        val cb = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                Thread {
                    var result: String = short
                    try {
                        repeat(5) {
                            val url = URL(result)
                            require(url.protocol == "https" && (url.host == "maps.app.goo.gl" || url.host == "goo.gl" || url.host == "google.com" || url.host.endsWith(".google.com")))
                            val connection = network.openConnection(url) as HttpURLConnection
                            try {
                                connection.instanceFollowRedirects = false; connection.connectTimeout = 1500; connection.readTimeout = 1500
                                val code = connection.responseCode
                                if (code in 300..399) {
                                    val next = connection.getHeaderField("Location") ?: return@repeat
                                    result = URL(url, next).toString()
                                }
                            } finally { connection.disconnect() }
                        }
                    } catch (_: Exception) { }
                    complete(result)
                }.start()
            }
        }
        callback = cb
        Networks.manager(this).requestNetwork(NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_CELLULAR)
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET).build(), cb)
        handler.postDelayed({ complete(text) }, 12000)
    }
    private fun complete(text: String) { runOnUiThread {
        if (!done.compareAndSet(false, true)) return@runOnUiThread
        startActivity(Intent(this, MainActivity::class.java).putExtra("share", text).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP))
        finish()
    } }
    override fun onDestroy() {
        done.set(true); handler.removeCallbacksAndMessages(null)
        callback?.let { Networks.manager(this).unregisterNetworkCallback(it) }
        super.onDestroy()
    }
}
