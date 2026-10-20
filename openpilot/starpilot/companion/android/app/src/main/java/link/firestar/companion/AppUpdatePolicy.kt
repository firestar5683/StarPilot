package link.firestar.companion

object AppUpdatePolicy {
    /** Android 12 has no runtime notification permission; Android 13 introduced it. */
    fun notificationsAllowed(sdk: Int, appEnabled: Boolean, channelEnabled: Boolean, permissionGranted: Boolean): Boolean =
        appEnabled && channelEnabled && (sdk < 33 || permissionGranted)

    fun newerVersion(available: String, installed: String): Boolean {
        fun parts(version: String): List<Long>? {
            if (!Regex("[0-9]+(?:\\.[0-9]+){1,3}").matches(version)) return null
            return version.split('.').map { it.toLongOrNull() ?: return null }
        }
        val next = parts(available) ?: return false
        val current = parts(installed) ?: return false
        for (index in 0 until maxOf(next.size, current.size)) {
            val comparison = (next.getOrElse(index) { 0L }).compareTo(current.getOrElse(index) { 0L })
            if (comparison != 0) return comparison > 0
        }
        return false
    }

    fun shouldNotify(available: String, installed: String, appAvailable: Boolean, notificationsEnabled: Boolean,
                     lastNotified: String): Boolean =
        appAvailable && notificationsEnabled && available != lastNotified && newerVersion(available, installed)
}
