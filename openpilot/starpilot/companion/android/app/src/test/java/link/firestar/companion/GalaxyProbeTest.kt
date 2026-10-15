package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test

class GalaxyProbeTest {
    @Test fun acceptsOnlyAnAuthenticatedLocalGalaxyAcknowledgement() {
        assertTrue(GalaxyProbe.accepts(200, "application/json", authenticated = true, localAccess = true))
        assertTrue(GalaxyProbe.accepts(200, "application/json; charset=utf-8", authenticated = true, localAccess = true))
        assertFalse(GalaxyProbe.accepts(404, "application/json", authenticated = true, localAccess = true))
        assertFalse(GalaxyProbe.accepts(200, "text/html", authenticated = true, localAccess = true))
        assertFalse(GalaxyProbe.accepts(200, "application/json", authenticated = false, localAccess = true))
        assertFalse(GalaxyProbe.accepts(200, "application/json", authenticated = true, localAccess = false))
    }
}
