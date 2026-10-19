package link.firestar.companion

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.widget.Toast

/** Package replacement kills the old process; Android delivers this to the new APK. */
class AppUpdateCompletion : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        val prefs = context.getSharedPreferences("companion", Context.MODE_PRIVATE)
        // The user may already have reopened the new version from Android's installer.
        if (prefs.getInt("lastOpenedAppCode", -1) == BuildConfig.VERSION_CODE) return
        prefs.edit().putInt("completedAppCode", BuildConfig.VERSION_CODE).apply()
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL, "App update completed", NotificationManager.IMPORTANCE_HIGH))
        if (!manager.areNotificationsEnabled() ||
            (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)) return
        val open = PendingIntent.getActivity(context, NOTIFICATION, Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        manager.notify(NOTIFICATION, Notification.Builder(context, CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle("StarPilot update installed")
            .setContentText("Version ${BuildConfig.VERSION_NAME} is ready. Tap to reopen StarPilot.")
            .setContentIntent(open).setAutoCancel(true)
            .addAction(Notification.Action.Builder(null, "Reopen", open).build()).build())
    }

    companion object {
        private const val CHANNEL = "app_update_completed"
        private const val NOTIFICATION = 3

        fun opened(context: Context) {
            val prefs = context.getSharedPreferences("companion", Context.MODE_PRIVATE)
            if (prefs.getInt("completedAppCode", -1) == BuildConfig.VERSION_CODE) {
                Toast.makeText(context, "Updated to StarPilot ${BuildConfig.VERSION_NAME}", Toast.LENGTH_LONG).show()
            }
            prefs.edit().putInt("lastOpenedAppCode", BuildConfig.VERSION_CODE).remove("completedAppCode").apply()
            context.getSystemService(NotificationManager::class.java).cancel(NOTIFICATION)
        }
    }
}
