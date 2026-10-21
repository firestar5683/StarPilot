package link.firestar.companion

import android.Manifest
import android.app.*
import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.os.Build
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

object AppUpdates {
    private const val CHANNEL = "app_updates"
    private const val NOTIFICATION = 2
    private const val JOB = 2
    const val ORIGIN_EXTRA = "updateOrigin"
    private val executor = Executors.newSingleThreadExecutor()
    private val checking = AtomicBoolean()
    private val notificationLock = Any()

    fun initialize(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL, "App updates", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "A notification when your comma has a newer StarPilot Android app"
        })
        // Remove an old update notification after that version has been installed.
        manager.activeNotifications.firstOrNull { it.id == NOTIFICATION }?.let {
            if (!AppUpdatePolicy.newerVersion(it.notification.extras.getString("availableVersion", ""), BuildConfig.VERSION_NAME)) {
                manager.cancel(NOTIFICATION)
            }
        }
        val scheduler = context.getSystemService(JobScheduler::class.java)
        if (scheduler.getPendingJob(JOB) == null) {
            val job = JobInfo.Builder(JOB, ComponentName(context, AppUpdateJob::class.java))
                .setPeriodic(TimeUnit.MINUTES.toMillis(15)).setPersisted(true)
            if (Build.VERSION.SDK_INT >= 28) {
                // Galaxy's hotspot can lack internet/validation; it is still usable for updates.
                job.setRequiredNetwork(NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                    .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                    .removeCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED).build())
            }
            scheduler.schedule(job.build())
        }
    }

    fun checkAsync(context: Context) {
        if (!checking.compareAndSet(false, true)) return
        val app = context.applicationContext
        executor.execute { try { runCatching { check(app) } } finally { checking.set(false) } }
    }

    /** Runs on a worker thread, always through the Wi-Fi network, independent of mobile-data sharing. */
    fun check(context: Context) {
        val prefs = context.getSharedPreferences("companion", Context.MODE_PRIVATE)
        val wifi = Networks.wifi(context) ?: Networks.wifi(context, false) ?: return
        val origin = if (Networks.wifi(context) != null) Networks.ORIGIN else
            Networks.localOrigin(prefs.getString("host", "") ?: "")?.takeIf { it != Networks.ORIGIN } ?: return
        // Screens are static files on comma, so refresh them even before the session check.
        GalaxyUpdates.refreshAsync(context, wifi.first, origin)
        val session = request(wifi.first, origin, "/api/auth/session")
        if (!session.first.optBoolean("authenticated") || !session.first.optBoolean("localAccess")) return
        val status = request(wifi.first, origin, "/api/companion/status", session.second).first
        if (Thread.currentThread().isInterrupted) return
        val available = status.optString("shippedVersion")
        val manager = context.getSystemService(NotificationManager::class.java)
        synchronized(notificationLock) {
            val allowed = AppUpdatePolicy.notificationsAllowed(Build.VERSION.SDK_INT, manager.areNotificationsEnabled(),
                manager.getNotificationChannel(CHANNEL)?.importance != NotificationManager.IMPORTANCE_NONE,
                context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED)
            if (!AppUpdatePolicy.shouldNotify(available, BuildConfig.VERSION_NAME, status.optBoolean("appAvailable"), allowed,
                    prefs.getString("notifiedAppVersion", "") ?: "")) return
            val open = PendingIntent.getActivity(context, NOTIFICATION,
                Intent(context, MainActivity::class.java).putExtra(ORIGIN_EXTRA, origin),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            val notification = Notification.Builder(context, CHANNEL).setSmallIcon(android.R.drawable.stat_sys_download_done)
                .setContentTitle("StarPilot app update available")
                .setContentText("Version $available is ready. Tap to open Galaxy and update the app.")
                .setContentIntent(open).setAutoCancel(true)
                .addExtras(android.os.Bundle().apply { putString("availableVersion", available) }).build()
            manager.notify(NOTIFICATION, notification)
            // Record only after posting; denied permission or a blocked channel must not consume the alert.
            prefs.edit().putString("notifiedAppVersion", available).apply()
        }
    }

    private fun request(network: Network, origin: String, path: String, cookie: String = ""): Pair<JSONObject, String> {
        val connection = network.openConnection(URL(origin + path)) as HttpURLConnection
        try {
            connection.connectTimeout = 3000; connection.readTimeout = 3000
            connection.instanceFollowRedirects = false
            if (cookie.isNotEmpty()) connection.setRequestProperty("Cookie", cookie)
            require(connection.responseCode == 200) { "Galaxy unavailable" }
            val body = connection.inputStream.bufferedReader().use { it.readText() }
            return JSONObject(body) to (connection.getHeaderField("Set-Cookie")?.substringBefore(';') ?: "")
        } finally { connection.disconnect() }
    }
}
