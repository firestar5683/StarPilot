package link.firestar.companion

import link.firestar.companion.AudioPairing.Open
import link.firestar.companion.AudioPairing.Outcome
import link.firestar.companion.AudioPairing.Prompt
import link.firestar.companion.AudioPairing.Snapshot
import org.junit.Assert.*
import org.junit.Test

class AudioPairingTest {
    private val comma = "AA:BB:CC:DD:EE:FF"
    private val idle = Snapshot(comma, "comma", null, null)
    private fun code(id: String = "a".repeat(32), kind: String = "confirmation", displayOnly: Boolean = false) = Prompt(id, kind, "123456", displayOnly)

    private class Run(snapshots: List<Snapshot?>, val open: Open = Open.OPENED, startBonded: Boolean = false, val bondOk: Boolean = true,
                      val accept: Boolean = true, val respondOk: Boolean = true, val bondsAfter: Int = Int.MAX_VALUE) {
        val remaining = snapshots.toMutableList()
        val calls = mutableListOf<String>()
        val bondedSet = if (startBonded) mutableSetOf("AA:BB:CC:DD:EE:FF") else mutableSetOf()
        var reads = 0
        fun pairing(attempts: Int = 5) = AudioPairing(
            status = { calls += "status"; if (remaining.size > 1) remaining.removeAt(0) else remaining.firstOrNull() },
            open = { calls += "open"; open },
            respond = { id, accepted -> calls += "respond:${id.take(1)}:$accepted"; respondOk },
            bonded = { if (++reads > bondsAfter) bondedSet += "AA:BB:CC:DD:EE:FF"; bondedSet },
            bond = { address -> calls += "bond:$address"; bondOk },
            confirm = { value -> calls += "confirm:$value"; accept },
            pause = {}, attempts = attempts,
        )
    }

    @Test fun pairsWhenCommaAsksForTheCodeAndTheBondAppears() {
        val run = Run(listOf(idle, idle, idle.copy(state = "pairing", prompt = code()), idle.copy(state = "paired")))
        assertEquals(Outcome.PAIRED, run.pairing().run())
        assertEquals(listOf("status", "open", "bond:$comma"), run.calls.take(3))
        assertTrue("confirm:123456" in run.calls && "respond:a:true" in run.calls)
    }

    @Test fun anAlreadyBondedCommaIsLeftAlone() {
        val run = Run(listOf(idle), startBonded = true)
        assertEquals(Outcome.ALREADY_PAIRED, run.pairing().run())
        assertEquals(listOf("status"), run.calls)
    }

    @Test fun olderCommaWithoutAdapterAddressOrWindowIsSkippedQuietly() {
        assertEquals(Outcome.UNSUPPORTED, Run(listOf(idle.copy(adapterAddress = ""))).pairing().run())
        val old = Run(listOf(idle), open = Open.UNSUPPORTED)
        assertEquals(Outcome.UNSUPPORTED, old.pairing().run())
        assertFalse(old.calls.any { it.startsWith("bond") })
        assertNull(AudioPairing.message(Outcome.UNSUPPORTED))
        assertNull(AudioPairing.message(Outcome.ALREADY_PAIRED))
    }

    @Test fun busyCommaNeverStartsABond() {
        val run = Run(listOf(idle), open = Open.BUSY)
        assertEquals(Outcome.BUSY, run.pairing().run())
        assertFalse(run.calls.any { it.startsWith("bond") })
        assertTrue(AudioPairing.message(Outcome.BUSY)!!.contains("busy"))
    }

    @Test fun declineIsReportedAndOnlyAnsweredOnce() {
        val prompting = idle.copy(state = "pairing", prompt = code())
        val run = Run(listOf(idle, prompting, prompting, idle.copy(state = "canceled")), accept = false)
        assertEquals(Outcome.DECLINED, run.pairing().run())
        assertEquals(1, run.calls.count { it.startsWith("respond") })
    }

    @Test fun displayOnlyAndNonConfirmationPromptsAreNeverApproved() {
        val run = Run(listOf(idle, idle.copy(state = "pairing", prompt = code(displayOnly = true)),
            idle.copy(state = "pairing", prompt = code(kind = "authorization")), idle.copy(state = "failed")))
        assertEquals(Outcome.FAILED, run.pairing().run())
        assertFalse(run.calls.any { it.startsWith("confirm") || it.startsWith("respond") })
    }

    @Test fun failuresAreReported() {
        assertEquals(Outcome.FAILED, Run(listOf(null)).pairing().run())
        assertEquals(Outcome.FAILED, Run(listOf(idle), open = Open.FAILED).pairing().run())
        assertEquals(Outcome.FAILED, Run(listOf(idle), bondOk = false).pairing().run())
        assertEquals(Outcome.FAILED, Run(listOf(idle, idle.copy(state = "pairing", prompt = code())), respondOk = false).pairing().run())
        assertEquals(Outcome.FAILED, Run(listOf(idle, idle.copy(state = "pairing"))).pairing(attempts = 3).run())
    }

    @Test fun anAppearingBondEndsThePollEvenIfCommaStatusLags() {
        val run = Run(listOf(idle, idle.copy(state = "pairing")), bondsAfter = 3)
        assertEquals(Outcome.PAIRED, run.pairing(attempts = 10).run())
    }
}
