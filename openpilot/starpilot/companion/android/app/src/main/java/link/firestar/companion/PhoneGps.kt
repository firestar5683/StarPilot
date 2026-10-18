package link.firestar.companion

/** Phone fix sent to comma's `POST /api/companion/location`; comma uses it only when its own GPS has no fix. */
object PhoneGps {
    const val PATH = "/api/companion/location"
    const val MAX_AGE_MS = 2000L

    data class Fix(
        val latitude: Double, val longitude: Double, val accuracy: Float, val timestamp: Long,
        val altitude: Double? = null, val verticalAccuracy: Float? = null,
        val speed: Float? = null, val speedAccuracy: Float? = null,
        val bearing: Float? = null, val bearingAccuracy: Float? = null,
    )

    /** Null when the fix is too old or has no usable position. Unknown values are left out. */
    fun payload(fix: Fix, ageMs: Long): Map<String, Any>? {
        if (ageMs !in 0..MAX_AGE_MS || !fix.latitude.isFinite() || !fix.longitude.isFinite() || !(fix.accuracy > 0f)) return null
        val values = linkedMapOf<String, Any>("latitude" to fix.latitude, "longitude" to fix.longitude,
            "horizontalAccuracy" to fix.accuracy.toDouble(), "ageMs" to ageMs, "timestamp" to fix.timestamp.coerceAtLeast(0))
        fun put(key: String, value: Number?) { value?.toDouble()?.takeIf { it.isFinite() && it >= 0 }?.let { values[key] = it } }
        fix.altitude?.takeIf { it.isFinite() }?.let { values["altitude"] = it }
        put("verticalAccuracy", fix.verticalAccuracy)
        put("speed", fix.speed)
        put("speedAccuracy", fix.speedAccuracy)
        if (fix.bearingAccuracy != null) { put("bearing", fix.bearing); put("bearingAccuracy", fix.bearingAccuracy) }
        return values
    }
}
