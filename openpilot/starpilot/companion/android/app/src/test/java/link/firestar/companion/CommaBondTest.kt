package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test

class CommaBondTest {
    private val comma = "39:90:21:64:07:00"

    @Test fun forgettingCommaInBluetoothSettingsEndsTheAppPairing() {
        assertTrue(CommaBond.forgotten(comma, "39:90:21:64:07:00", CommaBond.BOND_NONE))
        assertTrue(CommaBond.forgotten(comma, "39:90:21:64:07:00".lowercase(), CommaBond.BOND_NONE))
    }

    @Test fun otherDevicesAndOtherBondStatesAreIgnored() {
        assertFalse(CommaBond.forgotten(comma, "AA:BB:CC:DD:EE:FF", CommaBond.BOND_NONE))
        assertFalse(CommaBond.forgotten(comma, comma, 11))
        assertFalse(CommaBond.forgotten(comma, comma, 12))
        assertFalse(CommaBond.forgotten(null, comma, CommaBond.BOND_NONE))
        assertFalse(CommaBond.forgotten(comma, null, CommaBond.BOND_NONE))
    }

    @Test fun aBondMissingAtStartupMeansItWasForgottenWhileClosed() {
        assertTrue(CommaBond.missing(comma, setOf("AA:BB:CC:DD:EE:FF")))
        assertFalse(CommaBond.missing(comma, setOf("39:90:21:64:07:00")))
        assertFalse(CommaBond.missing(comma, setOf("39:90:21:64:07:00".lowercase())))
        assertFalse(CommaBond.missing(null, emptySet()))
    }
}
