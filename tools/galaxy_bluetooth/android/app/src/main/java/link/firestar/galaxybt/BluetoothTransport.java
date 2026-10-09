package link.firestar.galaxybt;

import android.annotation.SuppressLint;
import android.bluetooth.*;
import android.content.Context;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import org.json.JSONObject;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

/** One GATT operation at a time; failures close the session and never retry writes. */
@SuppressLint("MissingPermission")
public final class BluetoothTransport implements AutoCloseable {
    private static final class Event {
        final String kind; final UUID uuid; final byte[] data; final int status;
        Event(String kind, UUID uuid, byte[] data, int status) { this.kind = kind; this.uuid = uuid; this.data = data; this.status = status; }
    }
    private final Context context;
    private final Object requestLock = new Object();
    private final Object linkLock = new Object();
    private final HandlerThread callbacks = new HandlerThread("Galaxy Bluetooth");
    private final LinkedBlockingQueue<Event> events = new LinkedBlockingQueue<>(64);
    private volatile BluetoothGatt gatt;
    private volatile boolean connected, closed;
    private volatile byte[] activeTag;
    private volatile String catalogHash;
    private BluetoothGattCharacteristic rx, tx, info, notify;
    private byte[] key;
    private String session = "";
    private long counter;
    private int payload = 20;
    private boolean readStream, push;
    private final ArrayDeque<Event> buffered = new ArrayDeque<>();

    public BluetoothTransport(Context context) { this.context = context.getApplicationContext(); callbacks.start(); }
    public boolean isConnected() { return connected; }
    public String catalogHash() { return connected ? catalogHash : null; }
    private void emit(BluetoothGatt source, Event event) {
        synchronized (linkLock) {
            if (source != gatt) return;
            if (event.kind.equals("notify")) {
                byte[] tag = activeTag;
                if (tag == null) return;
                try { if (BridgeWire.notification(event.data, tag) == null) return; }
                catch (Exception failure) { event = new Event("invalid", null, new byte[0], 1); }
            }
            if (!events.offer(event)) disconnect();
        }
    }
    private final BluetoothGattCallback callback = new BluetoothGattCallback() {
        @Override public void onConnectionStateChange(BluetoothGatt g, int status, int state) {
            synchronized (linkLock) {
                if (state == BluetoothProfile.STATE_CONNECTED && status == BluetoothGatt.GATT_SUCCESS) emit(g, new Event("connected", null, new byte[0], status));
                else if (state == BluetoothProfile.STATE_DISCONNECTED || status != BluetoothGatt.GATT_SUCCESS) {
                    if (g == gatt) { connected = false; catalogHash = null; }
                    emit(g, new Event("lost", null, new byte[0], status));
                }
            }
        }
        @Override public void onMtuChanged(BluetoothGatt g, int mtu, int status) { emit(g, new Event("mtu", null, BridgeWire.number(mtu), status)); }
        @Override public void onServicesDiscovered(BluetoothGatt g, int status) { emit(g, new Event("services", null, new byte[0], status)); }
        @Override public void onServiceChanged(BluetoothGatt g) { synchronized (linkLock) { if (g == gatt) disconnect(); } }
        @Override public void onCharacteristicRead(BluetoothGatt g, BluetoothGattCharacteristic c, byte[] data, int status) { emit(g, new Event("read", c.getUuid(), data.clone(), status)); }
        @Override public void onCharacteristicRead(BluetoothGatt g, BluetoothGattCharacteristic c, int status) { if (Build.VERSION.SDK_INT < 33) emit(g, new Event("read", c.getUuid(), c.getValue() == null ? new byte[0] : c.getValue().clone(), status)); }
        @Override public void onCharacteristicWrite(BluetoothGatt g, BluetoothGattCharacteristic c, int status) { emit(g, new Event("write", c.getUuid(), new byte[0], status)); }
        @Override public void onDescriptorWrite(BluetoothGatt g, BluetoothGattDescriptor d, int status) { emit(g, new Event("descriptor", d.getUuid(), new byte[0], status)); }
        @Override public void onCharacteristicChanged(BluetoothGatt g, BluetoothGattCharacteristic c, byte[] data) { if (c.getUuid().equals(BridgeWire.NOTIFY)) emit(g, new Event("notify", c.getUuid(), data.clone(), 0)); }
        @Override public void onCharacteristicChanged(BluetoothGatt g, BluetoothGattCharacteristic c) { if (Build.VERSION.SDK_INT < 33 && c.getUuid().equals(BridgeWire.NOTIFY)) emit(g, new Event("notify", c.getUuid(), c.getValue() == null ? new byte[0] : c.getValue().clone(), 0)); }
    };
    private Event next(long deadline) throws Exception {
        long remaining = deadline - System.nanoTime();
        if (remaining <= 0) throw new IOException("Bluetooth timed out. Reconnect and check the setting before retrying.");
        Event e = events.poll(remaining, TimeUnit.NANOSECONDS);
        if (e == null) throw new IOException("Bluetooth timed out. Reconnect and check the setting before retrying.");
        if (e.kind.equals("lost") || e.kind.equals("invalid")) throw new IOException("Bluetooth connection ended. Reconnect and check any pending setting change.");
        return e;
    }
    private Event await(String kind, UUID uuid, long deadline) throws Exception {
        while (true) {
            Event e = next(deadline);
            if (e.kind.equals("notify")) {
                if (buffered.size() >= BridgeWire.WINDOW) throw new IOException("Bluetooth notification window exceeded.");
                buffered.add(e); continue;
            }
            if (!e.kind.equals(kind) || !Objects.equals(e.uuid, uuid)) throw new IOException("Unexpected Bluetooth operation result.");
            if (e.status != BluetoothGatt.GATT_SUCCESS && !kind.equals("mtu")) throw new IOException("Bluetooth operation failed. Reconnect to your comma.");
            return e;
        }
    }
    private BluetoothGatt current() throws IOException {
        BluetoothGatt value = gatt;
        if (value == null || closed) throw new IOException("Connect to your comma over Bluetooth first.");
        return value;
    }
    public void connect(BluetoothDevice device, String keyText, java.util.function.BooleanSupplier cancelled) throws Exception {
        synchronized (requestLock) {
            if (closed) throw new IOException("App is closing.");
            disconnect(); events.clear(); buffered.clear();
            key = BridgeWire.key(keyText); session = ""; counter = 0; push = false; readStream = false; payload = 20;
            try {
                synchronized (linkLock) {
                    if (closed || cancelled.getAsBoolean()) throw new IOException("Connection cancelled.");
                    gatt = device.connectGatt(context, false, callback, BluetoothDevice.TRANSPORT_LE, BluetoothDevice.PHY_LE_1M_MASK, new Handler(callbacks.getLooper()));
                    if (gatt == null) throw new IOException("Could not open the Bluetooth connection.");
                }
                await("connected", null, System.nanoTime() + TimeUnit.SECONDS.toNanos(20));
                current().requestConnectionPriority(BluetoothGatt.CONNECTION_PRIORITY_HIGH);
                if (current().requestMtu(517)) {
                    Event mtu = await("mtu", null, System.nanoTime() + TimeUnit.SECONDS.toNanos(10));
                    if (mtu.status == BluetoothGatt.GATT_SUCCESS) payload = Math.max(20, Math.min(512, BridgeWire.number(mtu.data, 0) - 3));
                }
                if (!current().discoverServices()) throw new IOException("Cannot discover the comma bridge.");
                await("services", null, System.nanoTime() + TimeUnit.SECONDS.toNanos(15));
                BluetoothGattService service = current().getService(BridgeWire.SERVICE);
                if (service == null) throw new IOException("Galaxy Bluetooth bridge was not found.");
                rx = service.getCharacteristic(BridgeWire.RX); tx = service.getCharacteristic(BridgeWire.TX);
                info = service.getCharacteristic(BridgeWire.INFO); notify = service.getCharacteristic(BridgeWire.NOTIFY);
                if (rx == null || tx == null || info == null || (rx.getProperties() & BluetoothGattCharacteristic.PROPERTY_WRITE) == 0) throw new IOException("Incompatible Bluetooth bridge.");
                byte[] challenge = read(info, System.nanoTime() + TimeUnit.SECONDS.toNanos(10));
                if (challenge.length != 17 || challenge[0] != 1) throw new IOException("Unsupported bridge version.");
                session = BridgeWire.hex(Arrays.copyOfRange(challenge, 1, 17));
                JSONObject response = exchange("/_bridge/health", "GET", new JSONObject(), new byte[0], true);
                if (response.getInt("status") != 200) throw new IOException("Pairing verification failed.");
                JSONObject health = new JSONObject(new String(BridgeWire.body(response), java.nio.charset.StandardCharsets.UTF_8));
                if (health.getInt("protocol") != 1 || !health.getString("transport").equals("bluetooth")) throw new IOException("Unsupported bridge protocol.");
                readStream = health.optBoolean("readStream", false);
                if (health.optBoolean("notificationStream", false)) {
                    if (notify == null || (notify.getProperties() & BluetoothGattCharacteristic.PROPERTY_NOTIFY) == 0) throw new IOException("Bridge services changed. Forget the old device pairing and reconnect.");
                    BluetoothGattDescriptor descriptor = notify.getDescriptor(BridgeWire.CCCD);
                    if (descriptor == null || !current().setCharacteristicNotification(notify, true)) throw new IOException("Cannot enable Bluetooth notifications.");
                    boolean started;
                    if (Build.VERSION.SDK_INT >= 33) started = current().writeDescriptor(descriptor, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE) == BluetoothStatusCodes.SUCCESS;
                    else { descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE); started = current().writeDescriptor(descriptor); }
                    if (!started) throw new IOException("Cannot subscribe to Bluetooth notifications.");
                    await("descriptor", BridgeWire.CCCD, System.nanoTime() + TimeUnit.SECONDS.toNanos(10));
                    push = true;
                }
                String digest = health.optString("catalogSHA256", "");
                synchronized (linkLock) {
                    if (gatt == null || closed || cancelled.getAsBoolean()) throw new IOException("Connection cancelled.");
                    catalogHash = digest.matches("[0-9a-f]{64}") ? digest : null;
                    connected = true;
                }
            } catch (Exception failure) { disconnect(); throw failure; }
        }
    }
    private void write(byte[] data, long deadline) throws Exception {
        boolean started;
        if (Build.VERSION.SDK_INT >= 33) started = current().writeCharacteristic(rx, data, BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT) == BluetoothStatusCodes.SUCCESS;
        else { rx.setWriteType(BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT); rx.setValue(data); started = current().writeCharacteristic(rx); }
        if (!started) throw new IOException("Cannot send Bluetooth request. Reconnect before retrying.");
        await("write", BridgeWire.RX, deadline);
    }
    private byte[] read(BluetoothGattCharacteristic c, long deadline) throws Exception {
        if (!current().readCharacteristic(c)) throw new IOException("Cannot read Bluetooth response.");
        return await("read", c.getUuid(), deadline).data;
    }
    public JSONObject request(String path, String method, JSONObject headers, byte[] body) throws Exception {
        synchronized (requestLock) {
            if (!connected) throw new IOException("Connect to your comma over Bluetooth first.");
            try { return exchange(path, method, headers, body, false); }
            catch (Exception failure) { disconnect(); throw failure; }
        }
    }
    private JSONObject exchange(String path, String method, JSONObject headers, byte[] body, boolean handshake) throws Exception {
        if (body.length > BridgeWire.MAX_BODY) throw new IOException("Upload exceeds the 1 MiB Bluetooth limit.");
        final String id = UUID.randomUUID().toString(), expectedSession = session;
        final long expectedCounter = ++counter;
        if (expectedCounter <= 0) throw new IOException("Reconnect to start a new Bluetooth session.");
        boolean notifications = push && !handshake, streaming = readStream && !handshake;
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(handshake ? 10 : 90);
        byte[] tag = BridgeWire.tag(expectedSession, expectedCounter);
        activeTag = notifications ? tag : null;
        buffered.clear();
        try {
            JSONObject message = new JSONObject().put("id", id).put("session", expectedSession).put("counter", expectedCounter)
                    .put("path", path).put("method", method).put("headers", headers).put("body", java.util.Base64.getEncoder().encodeToString(body)).put("responseCodec", 2);
            if (notifications) message.put("responseFlow", "notify-window8"); else if (streaming) message.put("responseFlow", "read-stream");
            byte[] frame = BridgeWire.seal(message, key, "request");
            int size = notifications ? payload : Math.min(180, payload);
            for (int start = 0, sequence = 0; start < frame.length; start += size - 5, sequence++)
                write(BridgeWire.join(new byte[]{1}, BridgeWire.number(sequence), Arrays.copyOfRange(frame, start, Math.min(frame.length, start + size - 5))), deadline);
            BridgeWire.Assembler assembler = new BridgeWire.Assembler(); int count = 0;
            while (true) {
                byte[] packet;
                if (notifications) {
                    Event e = buffered.isEmpty() ? next(Math.min(deadline, System.nanoTime() + TimeUnit.SECONDS.toNanos(15))) : buffered.removeFirst();
                    if (!e.kind.equals("notify")) throw new IOException("Unexpected Bluetooth response.");
                    packet = BridgeWire.notification(e.data, tag);
                    if (packet == null) continue;
                } else {
                    packet = read(tx, deadline);
                    if (Arrays.equals(packet, new byte[]{0})) { Thread.sleep(75); continue; }
                }
                byte[] complete = assembler.add(packet); count++;
                JSONObject response = null;
                if (complete != null) {
                    response = BridgeWire.open(complete, key, "response");
                    if (!id.equals(response.getString("id")) || !expectedSession.equals(response.getString("session")) || expectedCounter != response.getLong("counter")
                            || response.getInt("status") < 100 || response.getInt("status") > 599) throw new IOException("Bluetooth response identity did not match.");
                    BridgeWire.body(response);
                    if (!(response.get("headers") instanceof JSONObject)) throw new IOException("Invalid Bluetooth response headers.");
                }
                if (notifications && (response != null || count % BridgeWire.WINDOW == 0)) write(BridgeWire.join(new byte[]{4}, tag, Arrays.copyOfRange(packet, 1, 5)), deadline);
                else if (!notifications && (!streaming || response != null)) write(BridgeWire.join(new byte[]{2}, Arrays.copyOfRange(packet, 1, 5)), deadline);
                if (response != null) return response;
            }
        } finally { activeTag = null; buffered.clear(); }
    }
    public void disconnect() {
        synchronized (linkLock) {
            connected = false; activeTag = null; catalogHash = null;
            BluetoothGatt previous = gatt; gatt = null;
            if (previous != null) {
                try { previous.disconnect(); } catch (Exception ignored) {}
                try { previous.close(); } catch (Exception ignored) {}
            }
            events.clear(); events.offer(new Event("lost", null, new byte[0], 0));
        }
    }
    @Override public void close() { closed = true; disconnect(); callbacks.quitSafely(); }
}
