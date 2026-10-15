package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream

class AppInstallPolicyTest {
    @Test fun acceptsOnlyBoundedApkResponses() {
        assertTrue(AppInstallPolicy.accepts(200, "application/vnd.android.package-archive", 1024))
        assertTrue(AppInstallPolicy.accepts(200, "application/vnd.android.package-archive; charset=binary", 1024))
        assertFalse(AppInstallPolicy.accepts(302, "application/vnd.android.package-archive", 1024))
        assertFalse(AppInstallPolicy.accepts(200, "text/html", 1024))
        assertFalse(AppInstallPolicy.accepts(200, "application/vnd.android.package-archive", 0))
        assertFalse(AppInstallPolicy.accepts(200, "application/vnd.android.package-archive", AppInstallPolicy.MAX_APK_BYTES + 1))
    }

    @Test fun copiesExactlyTheAdvertisedLength() {
        val data = ByteArray(150000) { (it % 251).toByte() }
        val output = ByteArrayOutputStream()
        AppInstallPolicy.copyExact(ByteArrayInputStream(data), output, data.size.toLong())
        assertArrayEquals(data, output.toByteArray())
        assertThrows(IllegalArgumentException::class.java) {
            AppInstallPolicy.copyExact(ByteArrayInputStream(data), ByteArrayOutputStream(), data.size.toLong() - 1)
        }
        assertThrows(IllegalArgumentException::class.java) {
            AppInstallPolicy.copyExact(ByteArrayInputStream(data), ByteArrayOutputStream(), data.size.toLong() + 1)
        }
    }
}
