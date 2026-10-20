package link.firestar.companion

import org.junit.Assert.*
import org.junit.Test

class BleWireTest {
    private val key = ByteArray(32) { it.toByte() }
    private fun fixture(name: String) = javaClass.getResource("/ble/$name")!!.readText().trim()
    private fun hex(value: String) = value.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
    @Test fun pythonResponsesDecodeAndFragmentsReassemble() {
        for (name in listOf("plain", "compressed", "compact")) {
            val frame = hex(fixture("$name.hex"))
            for (size in listOf(20, 180, 512)) {
                val assembler = BleWire.Assembler()
                var result: ByteArray? = null
                for (packet in BleWire.packets(frame, size)) result = assembler.add(packet)
                val decoded = BleWire.decode(result!!, key)
                if (name == "compact") {
                    assertArrayEquals(ByteArray(16384) { (it % 256).toByte() }, decoded.body)
                    assertEquals("{\"id\":\"abc\",\"status\":200}", String(decoded.json))
                } else assertEquals(fixture("$name.json"), String(decoded.json))
            }
        }
    }
    @Test fun androidRequestMatchesPythonVector() {
        val actual = BleWire.seal("{\"method\":\"GET\",\"path\":\"/api/companion/status\"}".toByteArray(), key,
            nonce = ByteArray(12) { it.toByte() })
        assertArrayEquals(hex(fixture("request.hex")), actual)
    }
    @Test fun tamperingWrongDirectionAndOutOfOrderFail() {
        val frame = hex(fixture("plain.hex"))
        val encrypted = frame.copyOfRange(4, frame.size)
        assertThrows(Exception::class.java) { BleWire.open(encrypted, key, "request") }
        encrypted[15] = (encrypted[15].toInt() xor 1).toByte()
        assertThrows(Exception::class.java) { BleWire.open(encrypted, key) }
        assertThrows(IllegalArgumentException::class.java) { BleWire.Assembler().add(BleWire.packets(frame, 20)[1]) }
    }
}
