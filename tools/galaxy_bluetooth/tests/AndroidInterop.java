package link.firestar.galaxybt;

import org.json.JSONObject;
import java.nio.file.*;
import java.nio.ByteBuffer;
import java.util.*;

public final class AndroidInterop {
    private static void check(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) throws Exception {
        byte[] key = new byte[32]; for (int i = 0; i < key.length; i++) key[i] = (byte) i;
        byte[] request = Files.readAllBytes(Path.of(args[0]));
        JSONObject decoded = BridgeWire.open(Arrays.copyOfRange(request, 4, request.length), key, "request");
        check(decoded.getString("session").equals("01".repeat(16)));
        Files.write(Path.of(args[1]), BridgeWire.seal(decoded, key, "request"));
        byte[] expected = Files.readAllBytes(Path.of(args[3]));
        byte[] compact = Files.readAllBytes(Path.of(args[2]));
        JSONObject response = BridgeWire.open(Arrays.copyOfRange(compact, 4, compact.length), key, "response");
        check(Arrays.equals(BridgeWire.body(response), expected));
        byte[] tag = BridgeWire.tag("01".repeat(16), 2);
        ByteBuffer stream = ByteBuffer.wrap(Files.readAllBytes(Path.of(args[4])));
        BridgeWire.Assembler assembler = new BridgeWire.Assembler();
        java.io.ByteArrayOutputStream acks = new java.io.ByteArrayOutputStream();
        int count = 0; byte[] complete = null;
        while (stream.hasRemaining()) {
            byte[] notification = new byte[stream.getInt()]; stream.get(notification);
            byte[] packet = BridgeWire.notification(notification, tag);
            check(packet != null); complete = assembler.add(packet); count++;
            if (complete != null || count % 8 == 0) acks.write(BridgeWire.join(new byte[]{4}, tag, Arrays.copyOfRange(packet, 1, 5)));
        }
        check(complete != null && Arrays.equals(BridgeWire.body(BridgeWire.open(complete, key, "response")), expected));
        Files.write(Path.of(args[5]), acks.toByteArray());
        byte[] bad = Arrays.copyOfRange(compact, 4, compact.length); bad[bad.length - 1] ^= 1;
        try { BridgeWire.open(bad, key, "response"); throw new AssertionError("Tamper accepted"); } catch (javax.crypto.AEADBadTagException correct) {}
        try { BridgeWire.open(Arrays.copyOfRange(compact, 4, compact.length), key, "request"); throw new AssertionError("Wrong direction accepted"); } catch (javax.crypto.AEADBadTagException correct) {}
        BridgeWire.Assembler small = new BridgeWire.Assembler();
        try { small.add(BridgeWire.join(new byte[]{1}, BridgeWire.number(0), BridgeWire.number(BridgeWire.MAX_FRAME + 1))); throw new AssertionError("Oversized frame accepted"); } catch (IllegalArgumentException correct) {}
        for (String path : new String[]{"https://evil.example/api/params", "//evil.example/api/x", "/api/../x", "/api/%2e%2e/x", "/api/%252e/x", "/api/x#fragment", "/_bridge/health", "/outside", "/api/x%0a"}) {
            try { RequestPolicy.validate(path, "PUT"); throw new AssertionError("Bad path accepted: " + path); } catch (Exception correct) {}
        }
        RequestPolicy.validate("/api/params/all?galaxy_ble_settings=1", "GET");
        check(!RequestPolicy.local(new java.net.URI("https://appassets.androidplatform.net.evil.example/")));
        check(!RequestPolicy.local(new java.net.URI("https://user@appassets.androidplatform.net/")));
        System.out.println("Android production wire: Python exchange, compact binary bodies, notification framing/ACKs, tamper/direction/bounds and request policy passed");
    }
}
