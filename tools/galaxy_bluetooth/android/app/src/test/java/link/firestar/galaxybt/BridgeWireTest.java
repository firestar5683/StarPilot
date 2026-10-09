package link.firestar.galaxybt;

import org.json.JSONObject;
import org.junit.Test;
import static org.junit.Assert.*;
import java.util.*;
import java.util.zip.Deflater;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class BridgeWireTest {
    private final byte[] key = new byte[32];
    private byte[] encrypted(byte[] encoded) throws Exception {
        byte[] nonce = new byte[12]; Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, nonce));
        cipher.updateAAD("galaxy-ble-v1/response".getBytes(java.nio.charset.StandardCharsets.US_ASCII));
        return BridgeWire.join(nonce, cipher.doFinal(encoded));
    }
    private void reject(byte[] encoded) throws Exception {
        try { BridgeWire.open(encrypted(encoded), key, "response"); fail("Invalid envelope accepted"); } catch (Exception expected) {}
    }
    @Test public void rejectsUnknownCodecAndWrongLength() throws Exception {
        reject(BridgeWire.join(new byte[]{3}, BridgeWire.number(2), "{}".getBytes()));
        reject(BridgeWire.join(new byte[]{0}, BridgeWire.number(3), "{}".getBytes()));
        reject(BridgeWire.join(new byte[]{0}, BridgeWire.number(BridgeWire.MAX_FRAME + 1), "{}".getBytes()));
    }
    @Test public void rejectsTrailingJson() throws Exception {
        byte[] data = "{} garbage".getBytes();
        reject(BridgeWire.join(new byte[]{0}, BridgeWire.number(data.length), data));
    }
    @Test public void rejectsTruncatedCompression() throws Exception { reject(BridgeWire.join(new byte[]{1}, BridgeWire.number(100), new byte[]{1, 2, 3})); }
    @Test public void rejectsExpansionBeyondDeclaredSize() throws Exception {
        Deflater deflater = new Deflater(6, true); deflater.setInput(new byte[65536]); deflater.finish();
        byte[] zipped = new byte[1000]; int count = deflater.deflate(zipped); deflater.end();
        reject(BridgeWire.join(new byte[]{1}, BridgeWire.number(1), Arrays.copyOf(zipped, count)));
    }
    @Test public void rejectsMalformedBodyAndOversize() throws Exception {
        for (Object value : Arrays.asList(42, "not base64", "YQ", "A".repeat(((BridgeWire.MAX_BODY + 2) / 3) * 4 + 4))) {
            try { BridgeWire.body(new JSONObject().put("body", value)); fail("Invalid body accepted"); } catch (IllegalArgumentException expected) {}
        }
    }
    @Test public void rejectsOutOfOrderAndTrailingFragments() throws Exception {
        try { new BridgeWire.Assembler().add(BridgeWire.join(new byte[]{1}, BridgeWire.number(1), new byte[]{1})); fail(); } catch (IllegalArgumentException expected) {}
        byte[] frame = BridgeWire.join(BridgeWire.number(28), new byte[29]);
        try { new BridgeWire.Assembler().add(BridgeWire.join(new byte[]{1}, BridgeWire.number(0), frame)); fail(); } catch (IllegalArgumentException expected) {}
    }
    @Test public void ignoresOtherNotificationTags() throws Exception {
        byte[] tag = BridgeWire.tag("01".repeat(16), 1);
        byte[] other = BridgeWire.tag("01".repeat(16), 2);
        byte[] value = BridgeWire.join(new byte[]{3}, other, BridgeWire.number(0), new byte[]{1});
        assertNull(BridgeWire.notification(value, tag));
    }
    @Test public void acceptsOnlyLocalRelativeApiPaths() throws Exception {
        RequestPolicy.validate("/api/params?key=Metric", "PUT");
        assertTrue(RequestPolicy.local(new java.net.URI(RequestPolicy.ORIGIN)));
        assertFalse(RequestPolicy.local(new java.net.URI("http://appassets.androidplatform.net")));
        assertFalse(RequestPolicy.local(new java.net.URI("https://appassets.androidplatform.net:444")));
        try { RequestPolicy.validate("/api/x%0a", "GET"); fail(); } catch (IllegalArgumentException expected) {}
    }
}
