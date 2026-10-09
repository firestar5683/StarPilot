package link.firestar.galaxybt;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import java.security.KeyStore;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Only saves a key after the comma proves possession; excluded from Android backup. */
final class PairingKeyStore {
    private static final String ALIAS = "galaxy-pilot-pairing-v1";
    private final Context context;
    PairingKeyStore(Context context) { this.context = context; }
    private SecretKey wrappingKey() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore"); store.load(null);
        if (!store.containsAlias(ALIAS)) {
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setKeySize(256).build());
            generator.generateKey();
        }
        return (SecretKey) store.getKey(ALIAS, null);
    }
    String load() {
        try {
            String sealed = context.getSharedPreferences("pairing", Context.MODE_PRIVATE).getString("key", "");
            if (sealed.isEmpty()) return "";
            byte[] bytes = Base64.getDecoder().decode(sealed);
            if (bytes.length < 28) return "";
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, wrappingKey(), new GCMParameterSpec(128, java.util.Arrays.copyOf(bytes, 12)));
            String result = new String(cipher.doFinal(java.util.Arrays.copyOfRange(bytes, 12, bytes.length)), StandardCharsets.US_ASCII);
            BridgeWire.key(result); return result;
        } catch (Exception failure) { return ""; }
    }
    void save(String text) throws Exception {
        BridgeWire.key(text);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.ENCRYPT_MODE, wrappingKey());
        String sealed = Base64.getEncoder().encodeToString(BridgeWire.join(cipher.getIV(), cipher.doFinal(text.getBytes(StandardCharsets.US_ASCII))));
        if (!context.getSharedPreferences("pairing", Context.MODE_PRIVATE).edit().putString("key", sealed).commit()) throw new java.io.IOException("Could not save pairing key.");
    }
    void forget() { context.getSharedPreferences("pairing", Context.MODE_PRIVATE).edit().clear().apply(); }
}
