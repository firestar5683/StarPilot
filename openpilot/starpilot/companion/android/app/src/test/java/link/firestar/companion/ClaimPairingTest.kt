package link.firestar.companion

import java.math.BigInteger
import java.security.interfaces.ECPublicKey
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

/** The vector comes from comma's own claim.py (see galaxy_bluetooth/tests), so both sides agree byte for byte. */
class ClaimPairingTest {
    private fun hex(value: String) = value.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
    private val phone = ClaimPairing.privateKey(BigInteger("11".repeat(32), 16))
    private val challenge = ByteArray(16) { it.toByte() }
    private val phonePoint = hex("040217e617f0b6443928278f96999e69a23a4f2c152bdf6d6cdf66e5b80282d4ed194a7debcb97712d2dda3ca85aa8765a56f45fc758599652f2897c65306e5794")
    private val reply = hex("4743523104d65a93977caa3d1b081852ff57a79e465f1660577304baead505dd3a48589cf350185e895372df6221ea3a137557e473fddb6755f05bd507c3c533fce9c912856465666768696a6b6c6d6e6f56e085dc7bc3807c9c7cb045c4c1f175f83b778465883907450039ebf7bae2c056f9ce9975cfb418ec470cffe65a07209b6b0194c4f7858fdac068c0fb2f699f06cc4bfb9a8c6734d68a910c8d5329eadf05462b6c59013892e0522f5056974e80082afbb204b6cde770c4d5ed383ffe6f08909da1a7b716088c91d507bd197a3c8f48e8a53deaa7008f209ac1c78f733f078cd862345f0e2fab00241494bc7bc4be2a4769")

    @Test fun opensCommasReply() {
        val claim = ClaimPairing.open(reply, phone, challenge)
        assertEquals("ab".repeat(32), claim.key.joinToString("") { "%02x".format(it) })
        assertEquals("0a1b2c3d", claim.id)
        assertEquals("AA:BB:CC:DD:EE:FF", claim.adapterAddress)
        assertEquals("comma", claim.adapterName)
    }

    @Test fun readsEscapedAndMissingFields() {
        val json = """{"key":"${"cd".repeat(32)}","id":"0a1b2c3d","adapterAddress":"junk","adapterName":"Danny\u2019s \"comma\""}"""
        val claim = ClaimPairing.parse(json)
        assertEquals("Danny\u2019s \"comma\"", claim.adapterName)
        assertEquals("", claim.adapterAddress)
        assertThrows(IllegalArgumentException::class.java) { ClaimPairing.parse("""{"id":"0a1b2c3d"}""") }
        assertThrows(IllegalArgumentException::class.java) { ClaimPairing.parse("""{"key":"short"}""") }
        assertEquals("", ClaimPairing.parse("""{"key":"${"cd".repeat(32)}","id":"BAD"}""").id)
    }

    @Test fun derivesTheSameKeyAsComma() {
        val server = reply.copyOfRange(4, 69)
        assertArrayEquals(hex("3b5c0f6357da2c229949fb3695c3656c009af9b8fa4a7588ce991292c6eb73e0"), ClaimPairing.derive(phone, server, challenge))
    }

    @Test fun aWrongChallengeOrTamperedReplyIsRefused() {
        assertThrows(Exception::class.java) { ClaimPairing.open(reply, phone, ByteArray(16)) }
        assertThrows(Exception::class.java) { ClaimPairing.open(reply.copyOf().also { it[it.size - 1] = (it[it.size - 1].toInt() xor 1).toByte() }, phone, challenge) }
        assertThrows(Exception::class.java) { ClaimPairing.open(reply.copyOf().also { it[0] = 'X'.code.toByte() }, phone, challenge) }
        assertThrows(Exception::class.java) { ClaimPairing.open(reply.copyOfRange(0, 60), phone, challenge) }
    }

    @Test fun aReplyForAnotherPhoneIsRefused() {
        val other = ClaimPairing.newKeyPair()
        assertThrows(Exception::class.java) { ClaimPairing.open(reply, other.private, challenge) }
    }

    @Test fun requestsAreMagicPointAndName() {
        val pair = ClaimPairing.newKeyPair()
        val point = ClaimPairing.point(pair.public as ECPublicKey)
        assertEquals(65, point.size)
        assertEquals(4, point[0].toInt())
        val request = ClaimPairing.request(point, "Danny's Pixel 8")
        assertEquals("GCL1", String(request, 0, 4))
        assertArrayEquals(point, request.copyOfRange(4, 69))
        assertEquals("Danny's Pixel 8", String(request, 69, request.size - 69))
        assertEquals(40, ClaimPairing.request(point, "x".repeat(100)).size - 69)
        assertThrows(IllegalArgumentException::class.java) { ClaimPairing.request(ByteArray(65), "x") }
    }

    @Test fun publicPointsRoundTripThroughDerive() {
        val a = ClaimPairing.newKeyPair()
        val b = ClaimPairing.newKeyPair()
        val aPoint = ClaimPairing.point(a.public as ECPublicKey)
        val bPoint = ClaimPairing.point(b.public as ECPublicKey)
        assertArrayEquals(ClaimPairing.derive(a.private, bPoint, challenge), ClaimPairing.derive(b.private, aPoint, challenge))
        assertEquals(phonePoint.size, aPoint.size)
    }
}
