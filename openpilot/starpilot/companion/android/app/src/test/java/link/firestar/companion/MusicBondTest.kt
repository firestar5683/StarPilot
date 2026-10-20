package link.firestar.companion

import link.firestar.companion.MusicBond.Outcome
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MusicBondTest {
    private val comma = "AA:BB:CC:DD:EE:FF"

    private fun run(address: String = comma, bonded: MutableSet<String> = mutableSetOf(), attempts: Int = 5,
                    bond: (String) -> Boolean = { true }, onPause: () -> Unit = {}): Pair<Outcome, List<String>> {
        val asked = mutableListOf<String>()
        val outcome = MusicBond({ bonded.toSet() }, { asked += it; bond(it) }, { onPause() }, attempts).run(address)
        return outcome to asked
    }

    @Test fun olderCommaWithoutAnAddressIsSkippedQuietly() {
        assertEquals(Outcome.UNSUPPORTED to emptyList<String>(), run(""))
        assertEquals(Outcome.UNSUPPORTED to emptyList<String>(), run("not an address"))
        assertNull(MusicBond.message(Outcome.UNSUPPORTED))
    }

    @Test fun anAlreadyBondedCommaIsNotBondedAgain() {
        assertEquals(Outcome.ALREADY_PAIRED to emptyList<String>(), run(bonded = mutableSetOf(comma)))
        assertEquals(Outcome.ALREADY_PAIRED to emptyList<String>(), run(address = comma.lowercase(), bonded = mutableSetOf(comma)))
    }

    @Test fun bondingWaitsUntilAndroidReportsTheBond() {
        val bonded = mutableSetOf<String>()
        var pauses = 0
        val (outcome, asked) = run(bonded = bonded, onPause = { if (++pauses == 3) bonded += comma })
        assertEquals(Outcome.PAIRED, outcome)
        assertEquals(listOf(comma), asked)
    }

    @Test fun refusedOrTimedOutBondsFail() {
        assertEquals(Outcome.FAILED, run(bond = { false }).first)
        assertEquals(Outcome.FAILED, run(attempts = 3).first)
        assertTrue(MusicBond.message(Outcome.FAILED)!!.contains("music wasn't set up"))
    }
}
