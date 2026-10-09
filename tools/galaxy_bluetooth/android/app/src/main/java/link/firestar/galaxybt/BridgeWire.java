package link.firestar.galaxybt;

import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.charset.CodingErrorAction;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import java.util.UUID;
import java.util.zip.Deflater;
import java.util.zip.Inflater;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/** Matches the comma bridge's v1 protocol; contains no Android-specific APIs. */
public final class BridgeWire {
    public static final int MAX_FRAME = 2 * 1024 * 1024, MAX_BODY = 1024 * 1024, WINDOW = 8;
    public static final UUID SERVICE = UUID.fromString("bd490001-6dc1-4de7-a7d0-6cdb441f7650");
    public static final UUID RX = UUID.fromString("bd490002-6dc1-4de7-a7d0-6cdb441f7650");
    public static final UUID TX = UUID.fromString("bd490003-6dc1-4de7-a7d0-6cdb441f7650");
    public static final UUID INFO = UUID.fromString("bd490004-6dc1-4de7-a7d0-6cdb441f7650");
    public static final UUID NOTIFY = UUID.fromString("bd490005-6dc1-4de7-a7d0-6cdb441f7650");
    public static final UUID CCCD = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
    private static final SecureRandom RANDOM = new SecureRandom();
    private BridgeWire() {}

    public static byte[] key(String text) {
        if (!text.matches("[0-9a-fA-F]{64}")) throw new IllegalArgumentException("Pairing key must contain 64 hexadecimal characters.");
        return unhex(text);
    }
    public static byte[] unhex(String text) {
        if (text.length() % 2 != 0 || !text.matches("[0-9a-fA-F]+")) throw new IllegalArgumentException("Invalid hexadecimal value.");
        byte[] data = new byte[text.length() / 2];
        for (int i = 0; i < data.length; i++) data[i] = (byte) Integer.parseInt(text.substring(i * 2, i * 2 + 2), 16);
        return data;
    }
    public static String hex(byte[] data) {
        StringBuilder text = new StringBuilder();
        for (byte value : data) text.append(String.format("%02x", value & 255));
        return text.toString();
    }
    public static byte[] number(int value) { return ByteBuffer.allocate(4).putInt(value).array(); }
    public static int number(byte[] data, int offset) { return ByteBuffer.wrap(data, offset, 4).getInt(); }
    public static byte[] join(byte[]... parts) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        for (byte[] part : parts) out.write(part, 0, part.length);
        return out.toByteArray();
    }
    public static byte[] tag(String session, long counter) throws Exception {
        byte[] bytes = unhex(session);
        if (bytes.length != 16 || counter <= 0) throw new IllegalArgumentException("Invalid session.");
        return Arrays.copyOf(MessageDigest.getInstance("SHA-256").digest(join(bytes, ByteBuffer.allocate(8).putLong(counter).array())), 8);
    }
    private static byte[] deflate(byte[] data) {
        Deflater encoder = new Deflater(Deflater.DEFAULT_COMPRESSION, true);
        try {
            encoder.setInput(data); encoder.finish();
            ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] block = new byte[8192];
            while (!encoder.finished()) { int n = encoder.deflate(block); if (n <= 0) throw new IllegalArgumentException("Compression failed."); out.write(block, 0, n); }
            return out.toByteArray();
        } finally { encoder.end(); }
    }
    private static byte[] inflate(byte[] data, int length) throws Exception {
        Inflater decoder = new Inflater(true);
        try {
            decoder.setInput(data); ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] block = new byte[8192];
            while (!decoder.finished()) {
                int n = decoder.inflate(block);
                if (out.size() + n > length) throw new IllegalArgumentException("Decoded frame exceeds limit.");
                out.write(block, 0, n);
                if (n == 0 && !decoder.finished()) throw new IllegalArgumentException("Incomplete compressed frame.");
            }
            if (out.size() != length || decoder.getRemaining() != 0) throw new IllegalArgumentException("Incorrect compressed length.");
            return out.toByteArray();
        } finally { decoder.end(); }
    }
    public static byte[] seal(JSONObject message, byte[] key, String direction) throws Exception {
        byte[] plain = message.toString().getBytes(StandardCharsets.UTF_8);
        if (plain.length < 1 || plain.length > MAX_FRAME) throw new IllegalArgumentException("Request exceeds frame limit.");
        byte[] compressed = deflate(plain);
        byte[] encoded = join(new byte[]{(byte) (compressed.length < plain.length ? 1 : 0)}, number(plain.length), compressed.length < plain.length ? compressed : plain);
        byte[] nonce = new byte[12]; RANDOM.nextBytes(nonce);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, nonce));
        cipher.updateAAD(("galaxy-ble-v1/" + direction).getBytes(StandardCharsets.US_ASCII));
        byte[] frame = join(nonce, cipher.doFinal(encoded));
        if (frame.length > MAX_FRAME) throw new IllegalArgumentException("Encrypted request exceeds frame limit.");
        return join(number(frame.length), frame);
    }
    private static JSONObject json(byte[] bytes) throws Exception {
        String text = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        org.json.JSONTokener parser = new org.json.JSONTokener(text);
        Object value = parser.nextValue();
        if (!(value instanceof JSONObject) || parser.nextClean() != 0) throw new IllegalArgumentException("Invalid JSON envelope.");
        return (JSONObject) value;
    }
    public static JSONObject open(byte[] frame, byte[] key, String direction) throws Exception {
        if (frame.length < 28 || frame.length > MAX_FRAME) throw new IllegalArgumentException("Invalid frame length.");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, Arrays.copyOf(frame, 12)));
        cipher.updateAAD(("galaxy-ble-v1/" + direction).getBytes(StandardCharsets.US_ASCII));
        byte[] encoded = cipher.doFinal(Arrays.copyOfRange(frame, 12, frame.length));
        if (encoded.length < 5) throw new IllegalArgumentException("Invalid envelope.");
        int length = number(encoded, 1), codec = encoded[0] & 255;
        if (length < 1 || length > MAX_FRAME || codec > 2) throw new IllegalArgumentException("Unsupported envelope.");
        byte[] payload = Arrays.copyOfRange(encoded, 5, encoded.length);
        if (codec != 0) payload = inflate(payload, length);
        if (payload.length != length) throw new IllegalArgumentException("Incorrect envelope length.");
        if (codec != 2) return json(payload);
        if (payload.length < 5) throw new IllegalArgumentException("Invalid compact body.");
        int metadata = number(payload, 0);
        if (metadata < 1 || metadata > payload.length - 4 || payload.length - 4 - metadata > MAX_BODY) throw new IllegalArgumentException("Invalid compact body size.");
        JSONObject response = json(Arrays.copyOfRange(payload, 4, metadata + 4));
        if (response.has("body")) throw new IllegalArgumentException("Duplicate body.");
        response.put("body", Base64.getEncoder().encodeToString(Arrays.copyOfRange(payload, metadata + 4, payload.length)));
        return response;
    }
    public static byte[] body(JSONObject response) throws Exception {
        Object value = response.get("body");
        if (!(value instanceof String)) throw new IllegalArgumentException("Invalid response body.");
        String text = (String) value;
        if (text.length() > ((MAX_BODY + 2) / 3) * 4 || text.length() % 4 != 0) throw new IllegalArgumentException("Response body exceeds limit.");
        byte[] data = Base64.getDecoder().decode(text);
        if (data.length > MAX_BODY || !Base64.getEncoder().encodeToString(data).equals(text)) throw new IllegalArgumentException("Invalid response body.");
        return data;
    }
    public static byte[] notification(byte[] value, byte[] expectedTag) {
        if (value.length < 14 || value.length > 512 || value[0] != 3) throw new IllegalArgumentException("Invalid notification.");
        if (!MessageDigest.isEqual(Arrays.copyOfRange(value, 1, 9), expectedTag)) return null;
        return join(new byte[]{1}, Arrays.copyOfRange(value, 9, value.length));
    }
    public static final class Assembler {
        private final ByteArrayOutputStream data = new ByteArrayOutputStream();
        private int sequence = 0, length = -1;
        public byte[] add(byte[] packet) {
            if (packet.length < 6 || packet.length > 512 || packet[0] != 1 || number(packet, 1) != sequence++) throw new IllegalArgumentException("Out-of-order Bluetooth fragment.");
            if (data.size() + packet.length - 5 > MAX_FRAME + 4) throw new IllegalArgumentException("Frame exceeds limit.");
            data.write(packet, 5, packet.length - 5);
            byte[] all = data.toByteArray();
            if (length < 0 && all.length >= 4) { length = number(all, 0); if (length < 28 || length > MAX_FRAME) throw new IllegalArgumentException("Invalid encrypted length."); }
            if (length >= 0 && all.length >= length + 4) {
                if (all.length != length + 4) throw new IllegalArgumentException("Trailing Bluetooth bytes.");
                return Arrays.copyOfRange(all, 4, all.length);
            }
            return null;
        }
    }
}
