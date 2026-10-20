package link.firestar.companion

import java.math.BigInteger
import java.security.AlgorithmParameters
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.PrivateKey
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECParameterSpec
import java.security.spec.ECPoint
import java.security.spec.ECPrivateKeySpec
import java.security.spec.ECPublicKeySpec
import javax.crypto.Cipher
import javax.crypto.KeyAgreement
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Pairing with comma's open window: this phone sends a P-256 public key and gets its own key back, sealed under
 * an ECDH-derived key. See galaxy_bluetooth/README.md ("Pairing a phone") for the byte layout.
 */
object ClaimPairing {
    data class Claim(val key: ByteArray, val id: String, val adapterAddress: String, val adapterName: String)

    private val REQUEST_MAGIC = "GCL1".toByteArray()
    private val REPLY_MAGIC = "GCR1".toByteArray()
    private val INFO = "galaxy-claim-v1".toByteArray()
    private val AAD = "galaxy-claim-v1/reply".toByteArray()
    private val HEX64 = Regex("[0-9a-f]{64}")
    private val PHONE_ID = Regex("[0-9a-f]{8}")
    private val ADDRESS = Regex("(?i)[0-9a-f]{2}(?::[0-9a-f]{2}){5}")
    private const val POINT = 65

    private val curve: ECParameterSpec by lazy {
        AlgorithmParameters.getInstance("EC").apply { init(ECGenParameterSpec("secp256r1")) }.getParameterSpec(ECParameterSpec::class.java)
    }

    fun newKeyPair(): KeyPair = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()

    /** The 65-byte uncompressed point: 0x04 | X | Y. */
    fun point(key: ECPublicKey): ByteArray {
        fun fixed(value: BigInteger) = value.toByteArray().let { bytes ->
            when {
                bytes.size == 32 -> bytes
                bytes.size == 33 && bytes[0].toInt() == 0 -> bytes.copyOfRange(1, 33)
                bytes.size < 32 -> ByteArray(32 - bytes.size) + bytes
                else -> throw IllegalArgumentException("Invalid coordinate")
            }
        }
        return byteArrayOf(4) + fixed(key.w.affineX) + fixed(key.w.affineY)
    }

    fun request(publicPoint: ByteArray, name: String): ByteArray {
        require(publicPoint.size == POINT && publicPoint[0].toInt() == 4)
        return REQUEST_MAGIC + publicPoint + name.take(40).toByteArray(Charsets.UTF_8)
    }

    fun privateKey(scalar: BigInteger): PrivateKey = KeyFactory.getInstance("EC").generatePrivate(ECPrivateKeySpec(scalar, curve))

    private fun publicKey(point: ByteArray): ECPublicKey {
        require(point.size == POINT && point[0].toInt() == 4)
        val x = BigInteger(1, point.copyOfRange(1, 33))
        val y = BigInteger(1, point.copyOfRange(33, 65))
        return KeyFactory.getInstance("EC").generatePublic(ECPublicKeySpec(ECPoint(x, y), curve)) as ECPublicKey
    }

    private fun hmac(key: ByteArray, data: ByteArray): ByteArray =
        Mac.getInstance("HmacSHA256").apply { init(SecretKeySpec(key, "HmacSHA256")) }.doFinal(data)

    /** ECDH on P-256 then HKDF-SHA256 (RFC 5869) with the session challenge as salt. */
    fun derive(privateKey: PrivateKey, peerPoint: ByteArray, challenge: ByteArray): ByteArray {
        val secret = KeyAgreement.getInstance("ECDH").apply { init(privateKey); doPhase(publicKey(peerPoint), true) }.generateSecret()
        require(secret.size == 32)
        return hmac(hmac(challenge, secret), INFO + byteArrayOf(1))
    }

    /** Opens comma's reply. Throws when it is not for this request (wrong key, tampered, or not a claim reply). */
    fun open(reply: ByteArray, privateKey: PrivateKey, challenge: ByteArray): Claim {
        require(reply.size > 4 + POINT + 12 + 16 && reply.copyOfRange(0, 4).contentEquals(REPLY_MAGIC))
        val key = derive(privateKey, reply.copyOfRange(4, 4 + POINT), challenge)
        val nonce = reply.copyOfRange(4 + POINT, 4 + POINT + 12)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
        cipher.updateAAD(AAD)
        return parse(String(cipher.doFinal(reply, 4 + POINT + 12, reply.size - 4 - POINT - 12), Charsets.UTF_8))
    }

    fun parse(json: String): Claim {
        val hex = stringField(json, "key") ?: throw IllegalArgumentException("No key in reply")
        require(HEX64.matches(hex))
        val id = stringField(json, "id").orEmpty()
        val address = stringField(json, "adapterAddress").orEmpty()
        return Claim(hex.chunked(2).map { it.toInt(16).toByte() }.toByteArray(), if (PHONE_ID.matches(id)) id else "",
            if (ADDRESS.matches(address)) address.uppercase() else "", stringField(json, "adapterName").orEmpty().take(80))
    }

    /** The value of a top-level string field in comma's flat JSON object, with escapes decoded. */
    internal fun stringField(json: String, name: String): String? {
        val start = json.indexOf("\"$name\":\"").takeIf { it >= 0 }?.plus(name.length + 4) ?: return null
        val out = StringBuilder()
        var i = start
        while (i < json.length) {
            when (val c = json[i]) {
                '"' -> return out.toString()
                '\\' -> {
                    i++
                    when (val e = json.getOrNull(i) ?: return null) {
                        'n' -> out.append('\n'); 't' -> out.append('\t'); 'r' -> out.append('\r')
                        'b' -> out.append('\b'); 'f' -> out.append('\u000c')
                        'u' -> { out.append(json.substring(i + 1, minOf(i + 5, json.length)).toIntOrNull(16)?.toChar() ?: return null); i += 4 }
                        else -> out.append(e)
                    }
                }
                else -> out.append(c)
            }
            i++
        }
        return null
    }

    /** Asks the comma that has its pairing window open for a key. Blocks; call from a worker thread. */
    fun claim(transport: BleTransport, name: String): Claim {
        val pair = newKeyPair()
        val (challenge, reply) = transport.claim(request(point(pair.public as ECPublicKey), name))
        return open(reply, pair.private, challenge)
    }
}
