package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test

class PhoneGpsTest {
    private val fix = PhoneGps.Fix(40.0, -110.0, 5f, 1_790_000_000_000, altitude = 1200.0, speed = 20f, bearing = 90f, bearingAccuracy = 10f)

    @Test fun sendsKnownValues() {
        val payload = PhoneGps.payload(fix, 300)!!
        assertEquals(40.0, payload["latitude"]); assertEquals(300L, payload["ageMs"]); assertEquals(90.0, payload["bearing"])
        assertFalse("speedAccuracy" in payload)
    }

    @Test fun dropsBearingWithoutAccuracy() {
        val payload = PhoneGps.payload(fix.copy(bearingAccuracy = null), 300)!!
        assertFalse("bearing" in payload)
    }

    @Test fun rejectsOldOrUnusableFixes() {
        assertNull(PhoneGps.payload(fix, 2500))
        assertNull(PhoneGps.payload(fix, -1))
        assertNull(PhoneGps.payload(fix.copy(accuracy = 0f), 300))
        assertNull(PhoneGps.payload(fix.copy(latitude = Double.NaN), 300))
    }
}
