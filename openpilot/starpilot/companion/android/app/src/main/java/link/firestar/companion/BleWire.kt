package link.firestar.companion

import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.security.SecureRandom
import java.util.zip.Inflater
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/** Byte-compatible Galaxy BLE v1. Requests use codec 0; responses support all three codecs. */
object BleWire {
    const val MAX = 2 * 1024 * 1024
    fun seal(json: ByteArray, key: ByteArray, direction: String = "request", nonce: ByteArray = ByteArray(12).also { SecureRandom().nextBytes(it) }): ByteArray {
        require(json.size in 1..MAX && key.size == 32 && nonce.size == 12)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
        cipher.updateAAD("galaxy-ble-v1/$direction".toByteArray())
        val encoded = ByteBuffer.allocate(5 + json.size).put(0).putInt(json.size).put(json).array()
        val data = nonce + cipher.doFinal(encoded)
        require(data.size <= MAX)
        return ByteBuffer.allocate(4 + data.size).putInt(data.size).put(data).array()
    }
    data class Message(val json: ByteArray, val body: ByteArray? = null)
    fun open(data: ByteArray, key: ByteArray, direction: String = "response"): ByteArray = decode(data, key, direction).json
    fun decode(data: ByteArray, key: ByteArray, direction: String = "response"): Message {
        require(data.size in 33..MAX && key.size == 32)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, data.copyOfRange(0, 12)))
        cipher.updateAAD("galaxy-ble-v1/$direction".toByteArray())
        val encoded = cipher.doFinal(data.copyOfRange(12, data.size))
        require(encoded.size >= 5)
        val size = ByteBuffer.wrap(encoded, 1, 4).int
        require(size in 1..MAX)
        if (encoded[0].toInt() == 0) return Message(encoded.copyOfRange(5, encoded.size).also { require(it.size == size) })
        require(encoded[0].toInt() in 1..2)
        val inflater = Inflater(true)
        try {
            inflater.setInput(encoded, 5, encoded.size - 5)
            val result = ByteArray(size + 1)
            var count = 0
            while (!inflater.finished() && count < result.size) {
                val n = inflater.inflate(result, count, result.size - count)
                require(n > 0 || inflater.finished())
                count += n
            }
            require(inflater.finished() && inflater.remaining == 0 && count == size)
            if (encoded[0].toInt() == 2) {
                require(size >= 4)
                val metadata = ByteBuffer.wrap(result, 0, 4).int
                require(metadata in 1..(size - 4) && size - 4 - metadata <= 1024 * 1024)
                return Message(result.copyOfRange(4, 4 + metadata), result.copyOfRange(4 + metadata, size))
            }
            return Message(result.copyOf(size))
        } finally { inflater.end() }
    }
    fun packets(frame: ByteArray, size: Int): List<ByteArray> {
        require(size in 20..512 && frame.size <= MAX + 4)
        return (frame.indices step (size - 5)).mapIndexed { index, start ->
            val count = minOf(size - 5, frame.size - start)
            ByteBuffer.allocate(5 + count).put(1).putInt(index).put(frame, start, count).array()
        }
    }
    class Assembler {
        private val bytes = ByteArrayOutputStream()
        private var sequence = 0
        private var length: Int? = null
        fun add(packet: ByteArray): ByteArray? {
            require(packet.size >= 6 && packet[0].toInt() == 1 && ByteBuffer.wrap(packet, 1, 4).int == sequence++)
            require(bytes.size() + packet.size - 5 <= MAX + 4)
            bytes.write(packet, 5, packet.size - 5)
            if (length == null && bytes.size() >= 4) length = ByteBuffer.wrap(bytes.toByteArray(), 0, 4).int
            val expected = length ?: return null
            require(expected in 28..MAX && bytes.size() <= expected + 4)
            return if (bytes.size() == expected + 4) bytes.toByteArray().copyOfRange(4, expected + 4) else null
        }
    }
}
