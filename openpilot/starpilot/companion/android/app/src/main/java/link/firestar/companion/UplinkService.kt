package link.firestar.companion

import android.app.*
import android.content.Intent
import android.net.*
import android.os.IBinder
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.SecureRandom
import java.time.LocalDate
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class UplinkService : Service() {
    private val prefs by lazy { getSharedPreferences("companion", MODE_PRIVATE) }
    private val executor = Executors.newSingleThreadScheduledExecutor()
    @Volatile private var cellular: Network? = null
    private val sessionLock = Any()
    @Volatile private var stopped = false
    @Volatile private var socks: SocksServer? = null
    private var identity: String? = null
    private var cookie = ""
    private var bytes = 0L
    private var day = ""
    private val counterLock = Any()
    private var username = ""
    private var password = ""
    private val callback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) { cellular = network }
        override fun onLost(network: Network) { if (cellular == network) cellular = null }
    }
    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("uplink", "Phone internet", NotificationManager.IMPORTANCE_LOW))
        startForeground(1, notification("Waiting for Galaxy Wi-Fi and mobile data"))
        bytes = prefs.getLong("bytes", 0); day = prefs.getString("day", "")!!
        Networks.manager(this).requestNetwork(NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_CELLULAR)
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET).build(), callback)
        executor.scheduleWithFixedDelay({ tick() }, 0, 5, TimeUnit.SECONDS)
    }
    private fun notification(text: String): Notification {
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val stop = PendingIntent.getService(this, 1, Intent(this, UplinkService::class.java).setAction("stop"), PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, "uplink").setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle("StarPilot phone internet").setContentText(text).setContentIntent(open).setOngoing(true)
            .addAction(Notification.Action.Builder(null, "Stop", stop).build()).build()
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "stop" || !prefs.getBoolean("enabled", false)) {
            prefs.edit().putBoolean("enabled", false).apply(); stopSelf(); return START_NOT_STICKY
        }
        return START_STICKY
    }
    private fun reset() { synchronized(sessionLock) { socks?.close(); socks = null; identity = null; cookie = "" } }
    private fun secret(): String = ByteArray(24).also { SecureRandom().nextBytes(it) }.joinToString("") { "%02x".format(it) }
    private fun count(size: Int) { synchronized(counterLock) {
        val today = LocalDate.now().toString()
        if (day != today) { day = today; bytes = 0 }
        bytes += size
    } }
    private fun request(network: Network, path: String, body: JSONObject? = null): JSONObject {
        val connection = network.openConnection(URL(Networks.ORIGIN + path)) as HttpURLConnection
        try {
            connection.connectTimeout = 2000; connection.readTimeout = 2000; connection.instanceFollowRedirects = false
            connection.setRequestProperty("Origin", Networks.ORIGIN)
            if (cookie.isNotEmpty()) connection.setRequestProperty("Cookie", cookie)
            if (body != null) {
                connection.requestMethod = "POST"; connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toString().toByteArray()) }
            }
            require(connection.responseCode == 200) { "Galaxy unavailable" }
            connection.getHeaderField("Set-Cookie")?.let { cookie = it.substringBefore(';') }
            return JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
        } finally { connection.disconnect() }
    }
    private fun tick() {
        try {
            if (stopped || !prefs.getBoolean("enabled", false)) { reset(); return }
            val wifi = Networks.wifi(this)
            val cell = cellular
            if (wifi == null || cell == null || Networks.manager(this).getNetworkCapabilities(cell)?.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED) != true) { reset(); update("Waiting for Galaxy Wi-Fi and mobile data"); return }
            val current = "${wifi.first}:${wifi.second.hostAddress}:$cell"
            synchronized(sessionLock) {
                if (stopped) return
                if (identity != current) {
                    reset(); username = secret(); password = secret()
                    socks = SocksServer(wifi.second, AndroidCellularTransport(cell), username, password, ::count); identity = current
                }
            }
            // Refresh the short-lived LAN session every heartbeat, independent of WebView cookies.
            request(wifi.first, "/api/auth/session")
            val used = synchronized(counterLock) {
                count(0)
                prefs.edit().putLong("bytes", bytes).putString("day", day).apply()
                bytes
            }
            val response = request(wifi.first, "/api/companion/uplink", JSONObject().put("port", 1080).put("user", username)
                .put("pass", password).put("protocol", Networks.PROTOCOL).put("version", BuildConfig.VERSION_NAME).put("bytes", used))
            val deny = response.getJSONArray("uploadDenyHosts")
            socks?.deniedHosts = (0 until deny.length()).map { deny.getString(it).lowercase() }.toSet()
            if (!response.getBoolean("enabled")) { reset(); update("Enable phone internet in Galaxy"); return }
            update((if (response.optBoolean("active")) "Sharing mobile data with comma" else "Phone internet ready") + " · %.1f MB today".format(used / 1048576.0))
        } catch (_: Exception) {
            // Keep the SOCKS listener and credentials: the comma still routes to them until its lease expires.
            synchronized(sessionLock) { cookie = "" }
            update("Reconnecting to Galaxy…")
        }
    }
    private fun update(text: String) { if (stopped) return; getSystemService(NotificationManager::class.java).notify(1, notification(text)) }
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onDestroy() {
        stopped = true
        executor.shutdownNow()
        Networks.manager(this).unregisterNetworkCallback(callback)
        reset()
        synchronized(counterLock) { prefs.edit().putLong("bytes", bytes).putString("day", day).apply() }
        super.onDestroy()
    }
}
