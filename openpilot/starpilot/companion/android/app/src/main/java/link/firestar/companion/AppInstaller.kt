package link.firestar.companion

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Network
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Downloads a local, authenticated APK directly into Android's package installer. */
object AppInstaller {
    const val ACTION = "link.firestar.companion.APP_INSTALL_STATUS"
    private val executor = Executors.newSingleThreadExecutor()
    private val installing = AtomicBoolean()
    private val main = Handler(Looper.getMainLooper())

    fun start(context: Context, network: Network, origin: String): Boolean {
        if (!installing.compareAndSet(false, true)) return false
        val app = context.applicationContext
        Toast.makeText(app, "Downloading app update…", Toast.LENGTH_SHORT).show()
        executor.execute {
            try {
                downloadAndCommit(app, network, origin)
            } catch (error: Exception) {
                installing.set(false)
                main.post { Toast.makeText(app, "Update failed: ${error.message ?: "download unavailable"}", Toast.LENGTH_LONG).show() }
            }
        }
        return true
    }

    fun finished() { installing.set(false) }

    private fun sessionCookie(network: Network, origin: String): String {
        val connection = network.openConnection(URL("$origin/api/auth/session")) as HttpURLConnection
        try {
            connection.connectTimeout = 5000
            connection.readTimeout = 5000
            connection.instanceFollowRedirects = false
            check(connection.responseCode == 200) { "Galaxy authentication failed" }
            val body = connection.inputStream.bufferedReader().use { it.readText() }
            val status = JSONObject(body)
            check(status.optBoolean("authenticated") && status.optBoolean("localAccess")) { "Connect to Galaxy locally to update" }
            return connection.getHeaderField("Set-Cookie")?.substringBefore(';') ?: error("Galaxy session unavailable")
        } finally { connection.disconnect() }
    }

    private fun downloadAndCommit(context: Context, network: Network, origin: String) {
        require(Networks.localOrigin(origin) == origin) { "Invalid Galaxy address" }
        val connection = network.openConnection(URL("$origin/app.apk")) as HttpURLConnection
        var sessionId = -1
        var committed = false
        try {
            connection.connectTimeout = 5000
            connection.readTimeout = 30000
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Cookie", sessionCookie(network, origin))
            connection.setRequestProperty("Accept", "application/vnd.android.package-archive")
            val status = connection.responseCode
            val length = connection.contentLengthLong
            check(AppInstallPolicy.accepts(status, connection.contentType, length)) { "Invalid update response" }

            val installer = context.packageManager.packageInstaller
            val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL).apply {
                setAppPackageName(context.packageName)
                setSize(length)
                setOriginatingUri(Uri.parse("$origin/app.apk"))
                if (Build.VERSION.SDK_INT >= 31) setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_REQUIRED)
                if (Build.VERSION.SDK_INT >= 33) setPackageSource(PackageInstaller.PACKAGE_SOURCE_DOWNLOADED_FILE)
            }
            sessionId = installer.createSession(params)
            installer.openSession(sessionId).use { session ->
                session.openWrite("base.apk", 0, length).use { output ->
                    connection.inputStream.use { input -> AppInstallPolicy.copyExact(input, output, length) }
                    session.fsync(output)
                }
                val callback = Intent(context, AppInstallReceiver::class.java).setAction(ACTION)
                val flags = PendingIntent.FLAG_UPDATE_CURRENT or
                    (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
                val result = PendingIntent.getBroadcast(context, sessionId, callback, flags)
                session.commit(result.intentSender)
                committed = true
            }
        } finally {
            connection.disconnect()
            if (!committed && sessionId >= 0) runCatching { context.packageManager.packageInstaller.abandonSession(sessionId) }
        }
    }
}

class AppInstallReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != AppInstaller.ACTION) return
        when (val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                val confirmation = if (Build.VERSION.SDK_INT >= 33) {
                    intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    intent.getParcelableExtra(Intent.EXTRA_INTENT) as? Intent
                }
                if (confirmation == null) {
                    AppInstaller.finished()
                    Toast.makeText(context, "Android could not open the update confirmation", Toast.LENGTH_LONG).show()
                } else runCatching {
                    confirmation.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    context.startActivity(confirmation)
                }.onFailure {
                    AppInstaller.finished()
                    Toast.makeText(context, "Android could not open the update confirmation", Toast.LENGTH_LONG).show()
                }
            }
            PackageInstaller.STATUS_SUCCESS -> AppInstaller.finished()
            else -> {
                AppInstaller.finished()
                val detail = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)?.take(160)
                Toast.makeText(context, detail?.let { "Update failed: $it" } ?: "Update failed (Android status $status)", Toast.LENGTH_LONG).show()
            }
        }
    }
}
