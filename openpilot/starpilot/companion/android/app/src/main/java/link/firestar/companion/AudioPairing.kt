package link.firestar.companion

/**
 * After a phone is paired for Galaxy, also bond it with comma for Bluetooth music.
 * Comma opens a short pairing window; this phone starts the bond and approves the code.
 */
class AudioPairing(
    private val status: () -> Snapshot?,
    private val open: () -> Open,
    private val respond: (promptId: String, accepted: Boolean) -> Boolean,
    private val bonded: () -> Set<String>,
    private val bond: (address: String) -> Boolean,
    private val confirm: (code: String) -> Boolean,
    private val pause: (millis: Long) -> Unit = { Thread.sleep(it) },
    private val attempts: Int = 240,
) {
    data class Prompt(val id: String, val kind: String, val value: String, val displayOnly: Boolean)
    data class Snapshot(val adapterAddress: String, val adapterName: String, val state: String?, val prompt: Prompt?)
    enum class Open { OPENED, UNSUPPORTED, BUSY, FAILED }
    enum class Outcome { PAIRED, ALREADY_PAIRED, UNSUPPORTED, BUSY, DECLINED, FAILED }

    fun run(): Outcome {
        val first = status() ?: return Outcome.FAILED
        // An older comma reports no adapter address and has no pairing window.
        if (!ADDRESS.matches(first.adapterAddress)) return Outcome.UNSUPPORTED
        val comma = first.adapterAddress.uppercase()
        if (comma in bonded()) return Outcome.ALREADY_PAIRED
        when (open()) {
            Open.OPENED -> Unit
            Open.UNSUPPORTED -> return Outcome.UNSUPPORTED
            Open.BUSY -> return Outcome.BUSY
            Open.FAILED -> return Outcome.FAILED
        }
        if (!bond(comma)) return Outcome.FAILED
        var answered: String? = null
        var declined = false
        repeat(attempts) {
            if (comma in bonded()) return Outcome.PAIRED
            val current = status() ?: return Outcome.FAILED
            val prompt = current.prompt
            if (prompt != null && !prompt.displayOnly && prompt.id != answered && prompt.kind == "confirmation") {
                answered = prompt.id
                val accepted = confirm(prompt.value)
                if (!respond(prompt.id, accepted)) return Outcome.FAILED
                if (!accepted) declined = true
            }
            when (current.state) {
                "paired" -> return Outcome.PAIRED
                "failed", "canceled" -> return if (declined) Outcome.DECLINED else Outcome.FAILED
            }
            pause(500)
        }
        return Outcome.FAILED
    }

    companion object {
        private val ADDRESS = Regex("(?i)[0-9a-f]{2}(?::[0-9a-f]{2}){5}")

        fun message(outcome: Outcome): String? = when (outcome) {
            Outcome.PAIRED -> "Music is ready. Choose the comma as this phone's media audio output."
            Outcome.ALREADY_PAIRED -> null
            Outcome.UNSUPPORTED -> null
            Outcome.BUSY -> "Phone music wasn't set up because comma's Bluetooth is busy. Park, stop Android Auto pairing, then use Let a phone pair in Galaxy → Bluetooth."
            Outcome.DECLINED -> "Phone music pairing was declined."
            Outcome.FAILED -> "Phone music wasn't set up. Use Let a phone pair in Galaxy → Bluetooth to try again."
        }
    }
}
