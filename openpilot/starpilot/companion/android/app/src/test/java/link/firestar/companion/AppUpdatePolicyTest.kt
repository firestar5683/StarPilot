package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test

class AppUpdatePolicyTest {
    @Test fun android12DoesNotRequireRuntimeNotificationPermission() {
        assertTrue(AppUpdatePolicy.notificationsAllowed(31, true, true, false))
        assertTrue(AppUpdatePolicy.notificationsAllowed(32, true, true, false))
        assertFalse(AppUpdatePolicy.notificationsAllowed(33, true, true, false))
        assertTrue(AppUpdatePolicy.notificationsAllowed(33, true, true, true))
        assertFalse(AppUpdatePolicy.notificationsAllowed(31, false, true, true))
        assertFalse(AppUpdatePolicy.notificationsAllowed(31, true, false, true))
    }

    @Test fun comparesNumericVersionsAndRejectsDowngrades() {
        assertTrue(AppUpdatePolicy.newerVersion("1.1.10", "1.1.9"))
        assertTrue(AppUpdatePolicy.newerVersion("1.2", "1.1.99"))
        for ((available, installed) in listOf("1.1.7" to "1.1.7", "1.1.6" to "1.1.7", "1.1" to "1.1.0",
                "" to "1.1.7", "unknown" to "1.1.7", "1.1.8" to "", "1.1.8-beta" to "1.1.7",
                "99999999999999999999999.0" to "1.1.7")) {
            assertFalse("$available vs $installed", AppUpdatePolicy.newerVersion(available, installed))
        }
    }

    @Test fun alertsOncePerNewAvailableApkAndRequiresPermission() {
        assertTrue(AppUpdatePolicy.shouldNotify("1.1.8", "1.1.7", true, true, ""))
        assertFalse(AppUpdatePolicy.shouldNotify("1.1.8", "1.1.7", true, true, "1.1.8"))
        assertTrue(AppUpdatePolicy.shouldNotify("1.1.9", "1.1.7", true, true, "1.1.8"))
        assertFalse(AppUpdatePolicy.shouldNotify("1.1.8", "1.1.7", false, true, ""))
        assertFalse(AppUpdatePolicy.shouldNotify("1.1.8", "1.1.7", true, false, ""))
        assertFalse(AppUpdatePolicy.shouldNotify("1.1.7", "1.1.8", true, true, ""))
    }
}
