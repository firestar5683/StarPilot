package link.firestar.companion

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Explicit opt-in: the foreground service waits for a Galaxy Wi-Fi address. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val prefs = context.getSharedPreferences("companion", Context.MODE_PRIVATE)
        if (prefs.getBoolean("autoStart", false) && prefs.getBoolean("enabled", false)) {
            context.startForegroundService(Intent(context, UplinkService::class.java))
        }
    }
}
