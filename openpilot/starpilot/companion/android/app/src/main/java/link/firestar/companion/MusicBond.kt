package link.firestar.companion

/** After the app is paired, also bond this phone with comma for Bluetooth music. Comma's open window accepts it; Android asks the user once. */
class MusicBond(
    private val bonded: () -> Set<String>,
    private val bond: (address: String) -> Boolean,
    private val pause: (millis: Long) -> Unit = { Thread.sleep(it) },
    private val attempts: Int = 180,
) {
    enum class Outcome { PAIRED, ALREADY_PAIRED, UNSUPPORTED, FAILED }

    fun run(address: String): Outcome {
        // An older comma sends no Bluetooth address.
        if (!ADDRESS.matches(address)) return Outcome.UNSUPPORTED
        val comma = address.uppercase()
        if (comma in bonded()) return Outcome.ALREADY_PAIRED
        if (!bond(comma)) return Outcome.FAILED
        repeat(attempts) {
            if (comma in bonded()) return Outcome.PAIRED
            pause(500)
        }
        return Outcome.FAILED
    }

    companion object {
        private val ADDRESS = Regex("(?i)[0-9a-f]{2}(?::[0-9a-f]{2}){5}")

        fun message(outcome: Outcome): String? = when (outcome) {
            Outcome.PAIRED -> "Paired. For music, choose comma as this phone's media audio output."
            Outcome.ALREADY_PAIRED -> "Paired. This phone was already set up for music with comma."
            Outcome.UNSUPPORTED -> null
            Outcome.FAILED -> "The app is paired, but music wasn't set up. Open Pair phone on comma again (Settings > Bluetooth), then tap Pair with comma here."
        }
    }
}
