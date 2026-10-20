package link.firestar.companion

import android.Manifest
import android.app.*
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Base64
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** Sends this phone's GPS to comma about once a second, over Bluetooth or Galaxy Wi-Fi. */
class PhoneGpsService : Service(), LocationListener {
    companion object {
        fun enabled(prefs: android.content.SharedPreferences) = prefs.getBoolean("phoneGps", false)
    }
    private val prefs by lazy { getSharedPreferences("companion", MODE_PRIVATE) }
    private val executor = Executors.newSingleThreadScheduledExecutor()
    @Volatile private var latest: Location? = null
    @Volatile private var stopped = false
    private var sent = 0L
    private var cookie = ""
    private var lastBluetoothAttempt = 0L
    private var own: BleTransport? = null
    private var status = ""

    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("phone-gps", "Phone GPS", NotificationManager.IMPORTANCE_LOW))
        val first = notification("Waiting for GPS")
        try {
            if (Build.VERSION.SDK_INT >= 29) startForeground(2, first, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION) else startForeground(2, first)
            if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) throw SecurityException("Location permission")
            getSystemService(LocationManager::class.java).requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 0f, this, Looper.getMainLooper())
        } catch (_: Exception) {
            // Android refuses location in the background after the permission is withdrawn.
            prefs.edit().putBoolean("phoneGps", false).apply(); stopped = true; stopSelf(); return
        }
        executor.scheduleWithFixedDelay({ tick() }, 1, 1, TimeUnit.SECONDS)
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "stop" || !enabled(prefs)) {
            prefs.edit().putBoolean("phoneGps", false).apply(); stopSelf(); return START_NOT_STICKY
        }
        return START_STICKY
    }
    override fun onLocationChanged(location: Location) { latest = location }
    @Deprecated("Required before Android 10") override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
    override fun onProviderEnabled(provider: String) {}
    override fun onProviderDisabled(provider: String) {}

    private fun tick() {
        if (stopped) return
        val location = latest ?: return update("Waiting for GPS")
        if (location.elapsedRealtimeNanos == sent) return
        val age = (SystemClock.elapsedRealtimeNanos() - location.elapsedRealtimeNanos) / 1_000_000
        val payload = PhoneGps.payload(PhoneGps.Fix(location.latitude, location.longitude, location.accuracy, location.time,
            location.altitude.takeIf { location.hasAltitude() }, location.verticalAccuracyMeters.takeIf { location.hasVerticalAccuracy() },
            location.speed.takeIf { location.hasSpeed() }, location.speedAccuracyMetersPerSecond.takeIf { location.hasSpeedAccuracy() },
            location.bearing.takeIf { location.hasBearing() }, location.bearingAccuracyDegrees.takeIf { location.hasBearingAccuracy() }), age)
            ?: return update("Waiting for GPS")
        val body = JSONObject(payload).toString().toByteArray()
        try {
            send(body)
            sent = location.elapsedRealtimeNanos
            update("Sharing GPS with comma")
        } catch (_: Exception) { update("Waiting for comma") }
    }
    private fun send(body: ByteArray) {
        val ble = BleTransport.active?.takeIf { it.open } ?: Networks.wifi(this)?.let { wifi -> return post(wifi.first, body) } ?: bluetooth()
            ?: throw IllegalStateException("comma unavailable")
        val response = ble.request(JSONObject().put("method", "POST").put("path", PhoneGps.PATH)
            .put("headers", JSONObject().put("content-type", "application/json")).put("body", Base64.getEncoder().encodeToString(body)))
        require(response.getInt("status") == 200)
    }
    /** Opens Bluetooth only when no other part of the app holds or is opening the connection. */
    private fun bluetooth(): BleTransport? {
        val now = SystemClock.elapsedRealtime()
        if (BleTransport.active != null || BleTransport.busy || now - lastBluetoothAttempt < 15_000) return null
        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) return null
        lastBluetoothAttempt = now
        val pairing = PairingStore(this)
        val key = pairing.load() ?: return null
        val address = pairing.deviceAddress() ?: return null
        val transport = BleTransport(this, key)
        return try { transport.connect(address); own = transport; transport } catch (_: Exception) { transport.close(); null }
    }
    private fun post(network: android.net.Network, body: ByteArray) {
        for (attempt in 0..1) {
            if (cookie.isEmpty()) cookie = open(network, "/api/auth/session").run {
                try { getHeaderField("Set-Cookie")?.substringBefore(';') ?: "" } finally { disconnect() }
            }
            val connection = open(network, PhoneGps.PATH)
            try {
                connection.requestMethod = "POST"; connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body) }
                if (connection.responseCode == 200) return
                if (connection.responseCode != 401) error("Galaxy rejected the location")
            } finally { connection.disconnect() }
            cookie = ""
        }
        error("Galaxy session unavailable")
    }
    private fun open(network: android.net.Network, path: String) = (network.openConnection(URL(Networks.ORIGIN + path)) as HttpURLConnection).apply {
        connectTimeout = 2000; readTimeout = 2000; instanceFollowRedirects = false
        setRequestProperty("Origin", Networks.ORIGIN)
        if (cookie.isNotEmpty()) setRequestProperty("Cookie", cookie)
    }
    private fun notification(text: String): Notification {
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val stop = PendingIntent.getService(this, 1, Intent(this, PhoneGpsService::class.java).setAction("stop"), PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, "phone-gps").setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setContentTitle("StarPilot phone GPS").setContentText(text).setContentIntent(open).setOngoing(true)
            .addAction(Notification.Action.Builder(null, "Stop", stop).build()).build()
    }
    private fun update(text: String) {
        if (stopped || text == status) return
        status = text
        getSystemService(NotificationManager::class.java).notify(2, notification(text))
    }
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onDestroy() {
        stopped = true
        executor.shutdownNow()
        getSystemService(LocationManager::class.java).removeUpdates(this)
        own?.close()
        super.onDestroy()
    }
}
