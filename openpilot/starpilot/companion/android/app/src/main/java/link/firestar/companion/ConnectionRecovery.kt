package link.firestar.companion

/** Preserve connection work across a trip to Wi-Fi settings or another app. */
class ConnectionRecovery(private val search: (Boolean) -> Unit, private val connect: () -> Unit,
                         private val stopSearch: () -> Unit) {
    private var pending: (() -> Unit)? = null

    fun stopped(searchAutomatic: Boolean?, disconnected: Boolean) {
        pending = when {
            searchAutomatic != null -> { { search(searchAutomatic) } }
            disconnected -> connect
            else -> null
        }
        stopSearch()
    }

    fun resumed() {
        val action = pending
        pending = null
        action?.invoke()
    }
}
