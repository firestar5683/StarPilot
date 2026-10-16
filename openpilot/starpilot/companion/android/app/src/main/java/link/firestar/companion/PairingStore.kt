package link.firestar.companion

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class PairingStore(context: Context) {
    companion object { private val PHONE_ID = Regex("[0-9a-f]{8}") }
    private val prefs = context.getSharedPreferences("bluetooth-pairing", Context.MODE_PRIVATE)
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("galaxy-pairing", null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder("galaxy-pairing", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
            generateKey()
        }
    }
    /** [id] is comma's id for this phone's key (newer comma). The id it replaces is kept so comma can drop that entry. */
    fun save(value: ByteArray, id: String? = null) {
        require(value.size == 32)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val previous = id()
        prefs.edit().remove("deviceAddress").putString("key", Base64.getEncoder().encodeToString(cipher.iv + cipher.doFinal(value)))
            .apply { if (id != null && PHONE_ID.matches(id)) putString("id", id) else remove("id") }
            .apply { if (previous != null && previous != id) putString("previousId", previous) else remove("previousId") }
            .commit()
    }
    fun id(): String? = prefs.getString("id", null)?.takeIf { PHONE_ID.matches(it) }
    fun previousId(): String? = prefs.getString("previousId", null)?.takeIf { PHONE_ID.matches(it) }
    fun load(): ByteArray? = try {
        prefs.getString("key", null)?.let {
            val value = Base64.getDecoder().decode(it)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, value.copyOfRange(0, 12)))
            cipher.doFinal(value.copyOfRange(12, value.size)).also { decoded -> require(decoded.size == 32) }
        }
    } catch (_: Exception) { null }
    fun rememberDevice(address: String) {
        require(address.matches(Regex("(?i)[0-9a-f]{2}(?::[0-9a-f]{2}){5}")))
        prefs.edit().putString("deviceAddress", address.uppercase()).apply()
    }
    fun deviceAddress(): String? = prefs.getString("deviceAddress", null)?.takeIf {
        it.matches(Regex("(?i)[0-9a-f]{2}(?::[0-9a-f]{2}){5}"))
    }
    fun forget() { prefs.edit().clear().commit() }
}
