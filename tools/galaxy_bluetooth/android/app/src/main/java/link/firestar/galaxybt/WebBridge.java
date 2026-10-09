package link.firestar.galaxybt;

import android.content.Context;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.webkit.WebView;
import androidx.webkit.JavaScriptReplyProxy;
import androidx.webkit.WebMessageCompat;
import androidx.webkit.WebViewCompat;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.Iterator;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

/** Native messages are accepted only from the bundled top-level HTTPS page. */
final class WebBridge implements WebViewCompat.WebMessageListener {
    private final BluetoothTransport transport;
    private final ThreadPoolExecutor worker;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ConcurrentHashMap<String, AtomicBoolean> pending = new ConcurrentHashMap<>();
    private final Consumer<String> onError;
    private final byte[] catalog;
    private final String catalogHash;
    private volatile boolean enabled = true;
    WebBridge(Context context, BluetoothTransport transport, ThreadPoolExecutor worker, Consumer<String> onError) throws Exception {
        this.transport = transport; this.worker = worker; this.onError = onError;
        try (var input = context.getAssets().open("Web/assets/components/tools/device_settings_layout.json")) {
            java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
            byte[] block = new byte[8192]; int count;
            while ((count = input.read(block)) != -1) {
                if (out.size() + count > BridgeWire.MAX_BODY) throw new IllegalArgumentException("Bundled catalog exceeds limit.");
                out.write(block, 0, count);
            }
            catalog = out.toByteArray();
        }
        if (catalog.length > BridgeWire.MAX_BODY) throw new IllegalArgumentException("Bundled catalog exceeds limit.");
        catalogHash = BridgeWire.hex(MessageDigest.getInstance("SHA-256").digest(catalog));
    }
    void close() { enabled = false; pending.values().forEach(flag -> flag.set(true)); pending.clear(); }
    private void reply(JavaScriptReplyProxy proxy, String id, JSONObject response, String error) {
        main.post(() -> {
            if (!enabled) return;
            try {
                JSONObject value = new JSONObject().put("id", id).put("ok", error == null);
                if (error == null) value.put("response", response); else { value.put("error", error); onError.accept(error); }
                if (androidx.webkit.WebViewFeature.isFeatureSupported(androidx.webkit.WebViewFeature.WEB_MESSAGE_LISTENER))
                    proxy.postMessage(value.toString());
            } catch (Exception ignored) { /* The page may have closed while its response was drained. */ }
        });
    }
    @Override public void onPostMessage(WebView view, WebMessageCompat message, Uri sourceOrigin, boolean isMainFrame, JavaScriptReplyProxy proxy) {
        if (!enabled || !isMainFrame) return;
        try { if (!RequestPolicy.local(new java.net.URI(sourceOrigin.toString()))) return; }
        catch (Exception invalidOrigin) { return; }
        String id = "";
        try {
            String text = message.getData();
            if (text == null || text.length() > 2 * BridgeWire.MAX_BODY) throw new IllegalArgumentException("Request exceeds Bluetooth limit.");
            JSONObject input = new JSONObject(text); id = input.getString("id");
            if (!id.matches("[a-zA-Z0-9-]{1,80}")) throw new IllegalArgumentException("Invalid request identifier.");
            if (input.optBoolean("cancel", false)) { AtomicBoolean flag = pending.get(id); if (flag != null) flag.set(true); return; }
            if (pending.size() >= 32) throw new IllegalArgumentException("Bluetooth is busy. Wait for current requests to finish.");
            String path = input.getString("path"), method = input.getString("method"); RequestPolicy.validate(path, method);
            JSONObject headers = new JSONObject(), supplied = input.getJSONObject("headers");
            if (supplied.toString().length() > 8192) throw new IllegalArgumentException("Request headers exceed limit.");
            Iterator<String> names = supplied.keys();
            while (names.hasNext()) {
                String name = names.next(), lower = name.toLowerCase(java.util.Locale.ROOT);
                if (!new java.util.HashSet<>(java.util.Arrays.asList("content-type", "accept", "cookie", "range")).contains(lower)) continue;
                String value = supplied.getString(name);
                if (value.contains("\r") || value.contains("\n")) throw new IllegalArgumentException("Invalid request header.");
                headers.put(lower, value);
            }
            byte[] body = BridgeWire.body(new JSONObject().put("body", input.getString("body")));
            AtomicBoolean cancelled = new AtomicBoolean();
            if (pending.putIfAbsent(id, cancelled) != null) throw new IllegalArgumentException("Duplicate request identifier.");
            final String requestId = id;
            final long queued = System.nanoTime();
            try {
                worker.execute(() -> {
                    try {
                        if (!enabled || cancelled.get()) return;
                        if (System.nanoTime() - queued > java.util.concurrent.TimeUnit.SECONDS.toNanos(20)) throw new java.io.IOException("Request was not sent because Bluetooth is busy. Try again when loading finishes.");
                        if (!transport.isConnected()) throw new java.io.IOException("Reconnect to your comma over Bluetooth.");
                        JSONObject response;
                        if (method.equals("GET") && body.length == 0 && path.equals(RequestPolicy.CATALOG) && !headers.has("range") && catalogHash.equals(transport.catalogHash())) {
                            response = new JSONObject().put("status", 200).put("headers", new JSONObject().put("content-type", "application/json"))
                                    .put("body", Base64.getEncoder().encodeToString(catalog));
                        } else response = transport.request(path, method, headers, body);
                        if (!cancelled.get()) reply(proxy, requestId, response, null);
                    } catch (Exception failure) {
                        if (!cancelled.get()) reply(proxy, requestId, null, failure.getMessage() == null ? "Bluetooth request failed. Reconnect and check its result before retrying." : failure.getMessage());
                    } finally { pending.remove(requestId, cancelled); }
                });
            } catch (RuntimeException rejected) { pending.remove(id, cancelled); throw rejected; }
        } catch (Exception failure) { reply(proxy, id, null, failure.getMessage() == null ? "Invalid Galaxy request." : failure.getMessage()); }
    }
}
