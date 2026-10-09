package link.firestar.galaxybt;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.*;
import android.bluetooth.le.*;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.*;
import android.text.InputType;
import android.view.*;
import android.webkit.*;
import android.widget.*;
import androidx.webkit.*;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.*;
import java.util.concurrent.*;

public final class MainActivity extends androidx.activity.ComponentActivity {
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ThreadPoolExecutor worker = new ThreadPoolExecutor(1, 1, 0, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(32));
    private BluetoothTransport transport;
    private PairingKeyStore store;
    private LinearLayout root, pairing, results;
    private TextView status;
    private EditText key;
    private Button scan;
    private WebView web;
    private WebBridge bridge;
    private BluetoothLeScanner scanner;
    private final Set<String> seen = new HashSet<>();
    private boolean scanning, connecting;
    private volatile boolean destroyed;
    private final java.util.concurrent.atomic.AtomicInteger connectionAttempt = new java.util.concurrent.atomic.AtomicInteger();
    private final Runnable scanEnd = () -> {
        stopScan();
        if (seen.isEmpty() && !connecting && !destroyed) status.setText(R.string.ui_no_comma_found);
    };
    private static final int PERMISSION_REQUEST = 10, ENABLE_BLUETOOTH = 11;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        transport = new BluetoothTransport(this); store = new PairingKeyStore(this);
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(Color.rgb(23, 21, 29));
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                var bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        setContentView(root);
        LinearLayout toolbar = new LinearLayout(this); toolbar.setGravity(Gravity.CENTER_VERTICAL); toolbar.setPadding(dp(12), 0, dp(12), 0);
        TextView title = label(getString(R.string.ui_galaxy_bluetooth_pilot), 18); toolbar.addView(title, new LinearLayout.LayoutParams(0, dp(52), 1));
        Button disconnect = new Button(this); disconnect.setText(getString(R.string.ui_disconnect)); disconnect.setOnClickListener(v -> { connectionAttempt.incrementAndGet(); transport.disconnect(); showPairing(getString(R.string.ui_disconnected_scan_to_reconnect)); }); toolbar.addView(disconnect);
        root.addView(toolbar);
        status = label(getString(R.string.ui_connect_to_your_comma_over_bluetooth), 14); status.setPadding(dp(16), dp(8), dp(16), dp(8)); root.addView(status);
        pairing = new LinearLayout(this); pairing.setOrientation(LinearLayout.VERTICAL); pairing.setPadding(dp(20), dp(12), dp(20), 0);
        pairing.addView(label(getString(R.string.ui_pair_with_your_comma), 24));
        TextView intro = label(getString(R.string.ui_start_the_galaxy_bluetooth_bridge_on_your_comma_then_enter_its_pa), 16); intro.setPadding(0, dp(12), 0, dp(16)); pairing.addView(intro);
        key = new EditText(this); key.setTextColor(Color.WHITE); key.setHintTextColor(Color.LTGRAY); key.setHint(getString(R.string.ui_64_character_pairing_key)); key.setSingleLine(true); key.setImeOptions(android.view.inputmethod.EditorInfo.IME_ACTION_DONE);
        key.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD); key.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO); key.setText(store.load()); pairing.addView(key);
        scan = new Button(this); scan.setText(getString(R.string.ui_scan_for_comma)); scan.setOnClickListener(v -> startScan()); pairing.addView(scan);
        Button forget = new Button(this); forget.setText(getString(R.string.ui_forget_saved_key)); forget.setOnClickListener(v -> { connectionAttempt.incrementAndGet(); stopScan(); transport.disconnect(); synchronized (store) { store.forget(); } showPairing(getString(R.string.ui_saved_pairing_key_removed)); key.setText(""); status.setText(getString(R.string.ui_saved_pairing_key_removed)); }); pairing.addView(forget);
        ScrollView list = new ScrollView(this); results = new LinearLayout(this); results.setOrientation(LinearLayout.VERTICAL); list.addView(results); pairing.addView(list, new LinearLayout.LayoutParams(-1, 0, 1));
        root.addView(pairing, new LinearLayout.LayoutParams(-1, 0, 1));
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        getOnBackPressedDispatcher().addCallback(this, new androidx.activity.OnBackPressedCallback(true) {
            @Override public void handleOnBackPressed() { back(); }
        });
    }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private TextView label(String text, int size) { TextView view = new TextView(this); view.setText(text); view.setTextColor(Color.WHITE); view.setTextSize(size); view.setGravity(Gravity.CENTER_VERTICAL); return view; }
    private boolean permissions() {
        if (Build.VERSION.SDK_INT >= 31) return checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED;
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }
    @android.annotation.SuppressLint("MissingPermission") private void startScan() {
        if (connecting || scanning) return;
        getSystemService(android.view.inputmethod.InputMethodManager.class).hideSoftInputFromWindow(key.getWindowToken(), 0);
        try { BridgeWire.key(key.getText().toString().trim()); } catch (Exception failure) { status.setText(failure.getMessage()); return; }
        if (!permissions()) {
            requestPermissions(Build.VERSION.SDK_INT >= 31 ? new String[]{Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT} : new String[]{Manifest.permission.ACCESS_FINE_LOCATION}, PERMISSION_REQUEST); return;
        }
        BluetoothManager manager = getSystemService(BluetoothManager.class); BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
        if (adapter == null) { status.setText(getString(R.string.ui_bluetooth_is_unavailable_testing_needs_a_physical_android_phone_w)); return; }
        if (!adapter.isEnabled()) { startActivityForResult(new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE), ENABLE_BLUETOOTH); return; }
        if (Build.VERSION.SDK_INT <= 30) {
            boolean locationEnabled = Build.VERSION.SDK_INT >= 28
                    ? getSystemService(android.location.LocationManager.class).isLocationEnabled()
                    : android.provider.Settings.Secure.getInt(getContentResolver(), android.provider.Settings.Secure.LOCATION_MODE, 0) != 0;
            if (!locationEnabled) {
                status.setText(R.string.ui_older_android_location);
                startActivity(new Intent(android.provider.Settings.ACTION_LOCATION_SOURCE_SETTINGS));
                return;
            }
        }
        scanner = adapter.getBluetoothLeScanner();
        if (scanner == null) { status.setText(getString(R.string.ui_bluetooth_scanner_is_unavailable_turn_bluetooth_on_and_try_again)); return; }
        results.removeAllViews(); seen.clear(); scanning = true; scan.setEnabled(false); status.setText(getString(R.string.ui_looking_for_galaxy_bluetooth));
        try {
            scanner.startScan(Collections.singletonList(new ScanFilter.Builder().setServiceUuid(new ParcelUuid(BridgeWire.SERVICE)).build()), new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), scanCallback);
            main.postDelayed(scanEnd, 15000);
        } catch (Exception failure) { stopScan(); status.setText(getString(R.string.ui_could_not_scan_check_bluetooth_and_nearby_devices_permissions)); }
    }
    private final ScanCallback scanCallback = new ScanCallback() {
        @Override public void onScanResult(int type, ScanResult result) { main.post(() -> found(result)); }
        @Override public void onBatchScanResults(List<ScanResult> values) { main.post(() -> values.forEach(MainActivity.this::found)); }
        @Override public void onScanFailed(int error) { main.post(() -> { stopScan(); status.setText(getString(R.string.ui_bluetooth_scan_failed_wait_a_moment_and_try_again)); }); }
    };
    @android.annotation.SuppressLint("MissingPermission") private void found(ScanResult result) {
        if (!scanning || destroyed) return;
        BluetoothDevice device = result.getDevice(); if (!seen.add(device.getAddress())) return;
        String name = result.getScanRecord() == null ? null : result.getScanRecord().getDeviceName();
        Button item = new Button(this); item.setText(name == null || name.trim().isEmpty() ? "Galaxy Bluetooth" : name); item.setOnClickListener(v -> connect(device)); results.addView(item);
    }
    @android.annotation.SuppressLint("MissingPermission") private void stopScan() {
        main.removeCallbacks(scanEnd);
        if (scanning && scanner != null) { try { scanner.stopScan(scanCallback); } catch (Exception ignored) {} }
        scanning = false; if (scan != null) scan.setEnabled(!connecting);
    }
    private void connect(BluetoothDevice device) {
        if (connecting) return;
        String text = key.getText().toString().trim();
        final int attempt = connectionAttempt.incrementAndGet();
        stopScan(); connecting = true; scan.setEnabled(false); results.removeAllViews(); key.setEnabled(false); status.setText(getString(R.string.ui_connecting_and_verifying_your_pairing_key));
        worker.execute(() -> {
            try {
                transport.connect(device, text, () -> destroyed || connectionAttempt.get() != attempt);
                synchronized (store) {
                    if (destroyed || connectionAttempt.get() != attempt) throw new java.io.IOException("Connection cancelled.");
                    store.save(text);
                }
                main.post(() -> { if (destroyed || connectionAttempt.get() != attempt) return; connecting = false; key.setEnabled(true); scan.setEnabled(true); try { showGalaxy(); } catch (Exception failure) { transport.disconnect(); showPairing(failure.getMessage()); } });
            } catch (Exception failure) { transport.disconnect(); main.post(() -> { if (destroyed || connectionAttempt.get() != attempt) return; connecting = false; key.setEnabled(true); scan.setEnabled(true); status.setText(failure.getMessage() == null ? "Pairing failed. Check the bridge and pairing key." : failure.getMessage()); }); }
        });
    }
    private WebResourceResponse blocked(String message) { return new WebResourceResponse("text/plain", "UTF-8", 403, "Blocked", Collections.emptyMap(), new ByteArrayInputStream(message.getBytes(java.nio.charset.StandardCharsets.UTF_8))); }
    @android.annotation.SuppressLint("SetJavaScriptEnabled") private void showGalaxy() throws Exception {
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) throw new IllegalStateException("Update Android System WebView or Chrome, then reconnect.");
        pairing.setVisibility(View.GONE); getWindow().clearFlags(WindowManager.LayoutParams.FLAG_SECURE);
        web = new WebView(this); web.setBackgroundColor(Color.rgb(23, 21, 29));
        WebSettings settings = web.getSettings(); settings.setJavaScriptEnabled(true); settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false); settings.setAllowContentAccess(false); settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW); settings.setSupportMultipleWindows(false); settings.setMediaPlaybackRequiresUserGesture(true);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
        WebViewAssetLoader loader = new WebViewAssetLoader.Builder().addPathHandler("/", path -> {
            try {
                if (path.contains("\\") || path.contains("%") || path.contains("//") || Arrays.asList(path.split("/")).contains("..")) return blocked("Invalid asset path.");
                String file = path.equals("native-bridge.js") ? path : "Web/" + path;
                InputStream input = getAssets().open(file);
                String mime = file.endsWith(".js") ? "text/javascript" : file.endsWith(".css") ? "text/css" : file.endsWith(".html") ? "text/html" : file.endsWith(".json") ? "application/json" : file.endsWith(".svg") ? "image/svg+xml" : MimeTypeMap.getSingleton().getMimeTypeFromExtension(file.substring(file.lastIndexOf('.') + 1));
                WebResourceResponse response = new WebResourceResponse(mime == null ? "application/octet-stream" : mime, "UTF-8", input);
                Map<String, String> responseHeaders = new HashMap<>();
                responseHeaders.put("Content-Security-Policy", "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'");
                responseHeaders.put("Cache-Control", "no-store");
                response.setResponseHeaders(responseHeaders);
                return response;
            } catch (Exception failure) { return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", Collections.emptyMap(), new ByteArrayInputStream(new byte[0])); }
        }).build();
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                try { if (!RequestPolicy.local(new java.net.URI(request.getUrl().toString()))) return blocked("External resources are unavailable in this Bluetooth pilot."); }
                catch (Exception failure) { return blocked("Invalid resource URL."); }
                return loader.shouldInterceptRequest(request.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                try {
                    if (RequestPolicy.local(new java.net.URI(request.getUrl().toString()))) return false;
                    if (request.isForMainFrame() && request.hasGesture() && "https".equals(request.getUrl().getScheme())) startActivity(new Intent(Intent.ACTION_VIEW, request.getUrl()));
                } catch (Exception ignored) {}
                return true;
            }
            @Override public void onReceivedSslError(WebView view, android.webkit.SslErrorHandler handler, android.net.http.SslError error) { handler.cancel(); }
        });
        bridge = new WebBridge(this, transport, worker, message -> status.setText(message));
        if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER))
            WebViewCompat.addWebMessageListener(web, "GalaxyNative", Collections.singleton(RequestPolicy.ORIGIN), bridge);
        else throw new IllegalStateException("Update Android System WebView or Chrome, then reconnect.");
        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
        status.setText(getString(R.string.ui_connected_over_bluetooth_local_settings));
        web.loadUrl(RequestPolicy.ORIGIN + "/assets/mobile/index.html");
    }
    private void showPairing(String message) {
        connecting = false; key.setEnabled(true); scan.setEnabled(true);
        if (bridge != null) { bridge.close(); bridge = null; }
        if (web != null) { root.removeView(web); web.stopLoading(); web.destroy(); web = null; }
        pairing.setVisibility(View.VISIBLE); getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); status.setText(message == null ? "Reconnect to your comma." : message);
    }
    @Override public void onRequestPermissionsResult(int request, String[] names, int[] grants) { super.onRequestPermissionsResult(request, names, grants); if (request == PERMISSION_REQUEST) { if (permissions()) startScan(); else status.setText(getString(R.string.ui_allow_nearby_devices_or_location_on_older_android_to_scan_for_you)); } }
    @Override protected void onActivityResult(int request, int result, Intent data) { super.onActivityResult(request, result, data); if (request == ENABLE_BLUETOOTH && result == RESULT_OK) startScan(); }
    private void back() { if (web != null && web.canGoBack()) web.goBack(); else if (web != null) { transport.disconnect(); showPairing(getString(R.string.ui_disconnected_scan_to_reconnect)); } else finish(); }
    @Override protected void onStop() { stopScan(); if (web != null) { web.onPause(); web.pauseTimers(); } super.onStop(); }
    @Override protected void onResume() { super.onResume(); if (web != null) { web.onResume(); web.resumeTimers(); } }
    @Override protected void onDestroy() { destroyed = true; connectionAttempt.incrementAndGet(); stopScan(); if (bridge != null) bridge.close(); if (web != null) { web.resumeTimers(); web.destroy(); } transport.close(); worker.shutdownNow(); super.onDestroy(); }
}
