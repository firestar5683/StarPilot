package link.firestar.companion

import java.io.InputStream
import java.io.OutputStream

object AppInstallPolicy {
    const val MAX_APK_BYTES = 100L * 1024 * 1024
    private const val APK_TYPE = "application/vnd.android.package-archive"

    fun accepts(status: Int, contentType: String?, contentLength: Long): Boolean =
        status == 200 && contentType?.substringBefore(';')?.trim()?.equals(APK_TYPE, ignoreCase = true) == true &&
            contentLength in 1..MAX_APK_BYTES

    fun copyExact(input: InputStream, output: OutputStream, expected: Long) {
        require(expected in 1..MAX_APK_BYTES)
        val buffer = ByteArray(64 * 1024)
        var total = 0L
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            total += count
            require(total <= expected) { "The update was larger than advertised" }
            output.write(buffer, 0, count)
        }
        require(total == expected) { "The update download was incomplete" }
    }
}
