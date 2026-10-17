package link.firestar.companion

import org.junit.Assert.assertEquals
import org.junit.Test

class NetworksTest {
    @Test fun typedAddressAddsSchemeAndGalaxyPort() {
        assertEquals("http://192.168.1.10:8082", Networks.typedAddress(" 192.168.1.10 "))
        assertEquals("http://192.168.1.10:8082", Networks.typedAddress("192.168.1.10/"))
        assertEquals("http://10.0.0.4:8082", Networks.typedAddress("10.0.0.4:8082"))
    }

    @Test fun typedAddressKeepsExplicitSchemeAndPortForValidation() {
        assertEquals("http://192.168.1.10:8082", Networks.typedAddress("http://192.168.1.10:8082"))
        assertEquals("https://192.168.1.10:8082", Networks.typedAddress("https://192.168.1.10"))
        assertEquals("http://192.168.1.10:9000", Networks.typedAddress("192.168.1.10:9000"))
    }
}
