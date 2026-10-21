package link.firestar.companion

/** When this phone's Bluetooth bond with comma disappears, the app pairing should go with it. */
object CommaBond {
    const val BOND_NONE = 10

    /** A bond-state broadcast says comma's audio bond ended, for example after Forget in the phone's Bluetooth settings. */
    fun forgotten(remembered: String?, changed: String?, state: Int) =
        remembered != null && changed.equals(remembered, ignoreCase = true) && state == BOND_NONE

    /** The saved audio bond is no longer among the phone's bonded devices (forgotten while the app was closed). */
    fun missing(remembered: String?, bonded: Set<String>) =
        remembered != null && bonded.none { it.equals(remembered, ignoreCase = true) }
}
