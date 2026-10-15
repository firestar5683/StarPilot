package link.firestar.companion

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.pm.PackageManager
import java.net.HttpURLConnection
import java.net.URL
import java.util.Base64
import java.util.concurrent.*
import java.util.concurrent.atomic.AtomicInteger
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.webkit.*
import android.widget.*
import org.json.JSONObject
import java.io.ByteArrayInputStream

class MainActivity : Activity() {
    @Volatile private var web: WebView? = null
    private var ble: BleTransport? = null
    private val connectionGeneration = AtomicInteger()
    @Volatile private var bluetoothMode = false
    private val pairing by lazy { PairingStore(this) }
    private val jobs = ConcurrentHashMap<String, FutureTask<Unit>>()
    private val worker = ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, ArrayBlockingQueue(16))
    private val cachedOrigin = "https://galaxy-app.invalid"
    private var connectionStatus: TextView? = null
    private val recovery = ConnectionRecovery({ discoverLan(it) }, { connect() }, { stopDiscovery() })

    private var origin = Networks.ORIGIN
    private var share: String? = null
    private val prefs by lazy { getSharedPreferences("companion", MODE_PRIVATE) }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        share = intent.getStringExtra("share")?.take(8192)
        if (Build.VERSION.SDK_INT >= 33) requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        connect()
    }
    override fun onNewIntent(intent: Intent) { super.onNewIntent(intent); share = intent.getStringExtra("share")?.take(8192); connect() }
    private fun connect(host: String? = null) {
        stopDiscovery()
        connectionGeneration.incrementAndGet()
        jobs.values.forEach { it.cancel(false) }; jobs.clear(); worker.purge()
        ble?.close(); ble = null
        bluetoothMode = false
        val mode = prefs.getString("transport", "auto")
        if (host == null && mode == "bluetooth") { connectBluetooth(); return }
        val wifi = Networks.wifi(this) ?: Networks.wifi(this, false)
        if (wifi == null) {
            if (mode == "auto" && pairing.load() != null) connectBluetooth() else disconnected()
            return
        }
        val saved = Networks.localOrigin(prefs.getString("host", "") ?: "")
        if (host == null && Networks.wifi(this) == null && (saved == null || saved == Networks.ORIGIN)) {
            disconnected(); discoverLan(automatic = true); return
        }
        origin = host?.let { Networks.localOrigin(it) } ?: if (Networks.wifi(this) != null) Networks.ORIGIN else
            Networks.localOrigin(prefs.getString("host", Networks.ORIGIN)!!) ?: Networks.ORIGIN
        Networks.manager(this).bindProcessToNetwork(wifi.first)
        web?.destroy()
        val view = WebView(this)
        web = view
        view.setBackgroundColor(Color.rgb(7, 7, 18))
        view.settings.javaScriptEnabled = true
        view.settings.domStorageEnabled = true
        view.settings.allowFileAccess = false
        view.settings.allowContentAccess = false
        view.settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        CookieManager.getInstance().setAcceptThirdPartyCookies(view, false)
        view.addJavascriptInterface(Bridge(), "StarPilotApp")
        view.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(v: WebView, request: WebResourceRequest): Boolean {
                // No external document (including frames) ever receives the bridge.
                return Networks.localOrigin(request.url.toString()) != origin
            }
            override fun shouldInterceptRequest(v: WebView, request: WebResourceRequest): WebResourceResponse? {
                if (Networks.localOrigin(request.url.toString()) == origin) return null
                return WebResourceResponse("text/plain", "UTF-8", 403, "Local Galaxy only", emptyMap(), ByteArrayInputStream(byteArrayOf()))
            }
            override fun onReceivedError(v: WebView, request: WebResourceRequest, error: WebResourceError) {
                if (web === v && request.isForMainFrame) runOnUiThread {
                    if (web !== v) return@runOnUiThread
                    disconnected()
                    if (host == null && Networks.wifi(this@MainActivity) == null && Networks.wifi(this@MainActivity, false) != null)
                        discoverLan(automatic = true)
                    else if (prefs.getString("transport", "auto") == "auto" && pairing.load() != null) connectBluetooth()
                }
            }
            override fun onPageFinished(v: WebView, url: String) {
                if (web === v && Networks.localOrigin(url) == origin) { prefs.edit().putString("host", origin).apply(); share = null }
            }
        }
        view.setDownloadListener { url, _, _, _, _ ->
            if (Networks.localOrigin(url) == origin) startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        }
        view.setOnApplyWindowInsetsListener { v, insets ->
            v.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, insets.systemWindowInsetBottom); insets
        }
        showWeb(view, if (origin == Networks.ORIGIN) "Galaxy Wi-Fi" else "Local LAN")
        view.loadUrl(if (share != null) "$origin/?share=${Uri.encode(share)}#/navigation" else "$origin/#/galaxy")
        if (prefs.getBoolean("enabled", false)) startForegroundService(Intent(this, UplinkService::class.java))
    }
    private fun disconnected() {
        stopDiscovery()
        Networks.manager(this).bindProcessToNetwork(null)
        connectionGeneration.incrementAndGet(); ble?.close(); ble = null
        val previous = web; web = null
        previous?.removeJavascriptInterface("StarPilotApp"); previous?.stopLoading(); previous?.destroy()
        val panel = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(40, 100, 40, 40); setBackgroundColor(Color.rgb(7, 7, 18)) }
        connectionStatus = TextView(this).apply { text = "Connect to Galaxy\n\nUse comma Wi-Fi, a local LAN address, or pair Bluetooth while parked."; textSize = 22f; setTextColor(Color.WHITE) }
        panel.addView(connectionStatus)
        panel.addView(Button(this).apply { text = "Wi-Fi settings"; setOnClickListener { startActivity(Intent(Settings.ACTION_WIFI_SETTINGS)) } })
        panel.addView(Button(this).apply { text = "Try again"; setOnClickListener { connect() } })
        panel.addView(Button(this).apply { text = "Find comma on LAN"; setOnClickListener { discoverLan() } })
        panel.addView(Button(this).apply { text = "Bluetooth and connection options"; setOnClickListener { connections() } })
        val address = EditText(this).apply { hint = "Direct LAN: http://192.168.1.10:8082"; setSingleLine() }
        panel.addView(address)
        panel.addView(Button(this).apply { text = "Open local address"; setOnClickListener {
            if (Networks.localOrigin(address.text.toString()) != null) connect(address.text.toString())
            else address.error = "Use a private IPv4 address on port 8082"
        } })
        setContentView(ScrollView(this).apply { addView(panel) })
    }
    private fun showWeb(view: WebView, transport: String) {
        connectionStatus = null
        val panel = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0, 32, 0, 0) }
        panel.addView(Button(this).apply { text = "$transport · Connections"; setOnClickListener { connections() } })
        panel.addView(view, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(panel)
    }
    private fun message(text: String) { if (isFinishing || isDestroyed) return; AlertDialog.Builder(this).setMessage(text).setPositiveButton("OK", null).show() }
    private fun connections() {
        val options = arrayOf("Automatic (Wi-Fi first)", "Galaxy Wi-Fi / LAN only", "Bluetooth only", "Enter LAN address", "Pair Bluetooth using Wi-Fi / LAN", "Paste Bluetooth pairing code", "Forget Bluetooth on this phone", "Revoke all paired phones on comma", "Find Galaxy on LAN")
        AlertDialog.Builder(this).setTitle("Galaxy connection").setItems(options) { _, which ->
            when (which) {
                0, 1, 2 -> { prefs.edit().putString("transport", arrayOf("auto", "wifi", "bluetooth")[which]).apply(); connect() }
                3 -> {
                    val field = EditText(this).apply { setText(prefs.getString("host", Networks.ORIGIN)); setSingleLine() }
                    AlertDialog.Builder(this).setTitle("Local Galaxy address").setView(field).setPositiveButton("Connect") { _, _ ->
                        val host = Networks.localOrigin(field.text.toString())
                        if (host == null) message("Use a private IPv4 address on port 8082") else {
                            prefs.edit().putString("host", host).putString("transport", "wifi").apply(); connect(host)
                        }
                    }.setNegativeButton("Cancel", null).show()
                }
                4 -> pairOverWifi(false)
                5 -> {
                    val field = EditText(this).apply { hint = "galaxy-bluetooth JSON or 64-character key" }
                    AlertDialog.Builder(this).setTitle("Pair with comma").setView(field).setPositiveButton("Save") { _, _ ->
                        try {
                            val raw = field.text.toString().trim()
                            savePairing(if (raw.startsWith("{")) JSONObject(raw) else JSONObject().put("type", "galaxy-bluetooth").put("version", 1).put("key", raw))
                            message("Bluetooth pairing saved. Choose Bluetooth only to connect.")
                        } catch (_: Exception) { message("Invalid Galaxy Bluetooth pairing code") }
                    }.setNegativeButton("Cancel", null).show()
                }
                6 -> { pairing.forget(); ble?.close(); disconnected() }
                8 -> discoverLan()
                7 -> AlertDialog.Builder(this).setMessage("Revoke every phone using this comma's Galaxy Bluetooth key, including iPhones? Pair again afterward.")
                    .setPositiveButton("Revoke") { _, _ -> pairOverWifi(true) }.setNegativeButton("Cancel", null).show()
            }
        }.show()
    }
    private var discovery: LanDiscovery? = null
    private var discoveryAutomatic = false
    private var lanPicker: AlertDialog? = null
    private fun stopDiscovery() {
        discovery?.close(); discovery = null
        lanPicker?.dismiss(); lanPicker = null
    }
    private fun connectionStatus(text: String) { connectionStatus?.text = "Connect to Galaxy\n\n$text" }
    private fun bluetoothFallback(): Boolean {
        if (prefs.getString("transport", "auto") != "auto" || pairing.load() == null) return false
        connectBluetooth(); return true
    }
    private fun discoverLan(automatic: Boolean = false) {
        val wifi = Networks.wifi(this, false)
        if (wifi == null) {
            if (automatic) { if (!bluetoothFallback()) connectionStatus("Join the same Wi-Fi network as comma first.") }
            else message("Join the same Wi-Fi network as comma first")
            return
        }
        stopDiscovery()
        discoveryAutomatic = automatic
        val generation = connectionGeneration.get()
        val search = LanDiscovery(this, wifi.first) { hosts, error ->
            discovery = null
            if (!isFinishing && !isDestroyed && generation == connectionGeneration.get()) {
                fun select(host: String) {
                    val edit = prefs.edit().putString("host", host)
                    if (!automatic) edit.putString("transport", "wifi")
                    edit.apply(); connect(host)
                }
                fun cancel() {
                    if (generation == connectionGeneration.get() && web == null && ble == null) bluetoothFallback()
                }
                if (hosts.isEmpty()) {
                    val text = error ?: "No comma found. Keep Galaxy enabled on comma and connect both devices to the same Wi-Fi. Comma prepares discovery automatically while parked with internet; the first setup may take a few minutes. Try again shortly, or enter its IP address if your router blocks multicast."
                    if (automatic) { if (!bluetoothFallback()) connectionStatus(text) } else message(text)
                } else if (automatic && hosts.size == 1) select(hosts.single())
                else {
                    val picker = AlertDialog.Builder(this).setTitle("Choose your comma on this trusted LAN")
                        .setItems(hosts.toTypedArray()) { _, which -> if (generation == connectionGeneration.get()) select(hosts[which]) }
                        .setNegativeButton("Cancel") { _, _ -> cancel() }.setOnCancelListener { cancel() }.create()
                    picker.setOnDismissListener { if (lanPicker === picker) lanPicker = null }
                    lanPicker = picker; picker.show()
                }
            }
        }
        discovery = search
        if (automatic) connectionStatus("Looking for comma on LAN…")
        else Toast.makeText(this, "Looking for comma on LAN…", Toast.LENGTH_LONG).show()
        search.start()
    }
    private fun savePairing(value: JSONObject) {
        require(value.getString("type") == "galaxy-bluetooth" && value.getInt("version") == 1)
        val hex = value.getString("key")
        require(hex.matches(Regex("[0-9a-fA-F]{64}")))
        pairing.save(hex.chunked(2).map { it.toInt(16).toByte() }.toByteArray())
    }
    private fun pairOverWifi(rotate: Boolean) {
        val wifi = Networks.wifi(this) ?: Networks.wifi(this, false)
        if (wifi == null) { message("Join Galaxy Wi-Fi or the comma's trusted LAN first"); return }
        val host = if (Networks.wifi(this) != null) Networks.ORIGIN else Networks.localOrigin(prefs.getString("host", "") ?: "")
        if (host == null) { message("Enter the comma's LAN address first"); return }
        Thread {
            try {
                fun connection(path: String) = (wifi.first.openConnection(URL(host + path)) as HttpURLConnection).apply {
                    instanceFollowRedirects = false; connectTimeout = 5000; readTimeout = 5000
                    setRequestProperty("Origin", host)
                }
                val auth = connection("/api/auth/session")
                val cookie = try {
                    check(auth.responseCode == 200) { "Galaxy authentication failed" }
                    auth.getHeaderField("Set-Cookie")?.substringBefore(';') ?: error("Galaxy session unavailable")
                } finally { auth.disconnect() }
                val call = connection("/api/companion/bluetooth")
                val result = try {
                    call.requestMethod = "POST"; call.doOutput = true
                    call.setRequestProperty("Cookie", cookie); call.setRequestProperty("Content-Type", "application/json")
                    call.outputStream.use { it.write(JSONObject().put("rotate", rotate).toString().toByteArray()) }
                    val status = call.responseCode
                    val body = (if (status == 200) call.inputStream else call.errorStream).use { input ->
                        val bytes = java.io.ByteArrayOutputStream()
                        val buffer = ByteArray(1024)
                        while (true) {
                            val count = input.read(buffer)
                            if (count < 0) break
                            require(bytes.size() + count <= 8192) { "Invalid pairing response" }
                            bytes.write(buffer, 0, count)
                        }
                        bytes.toByteArray()
                    }
                    val value = JSONObject(String(body))
                    check(status == 200) { value.optString("error", "Pairing failed") }; value
                } finally { call.disconnect() }
                if (rotate) { pairing.forget(); ble?.close() } else savePairing(result)
                runOnUiThread { message(if (rotate) "All Bluetooth phones revoked. Pair again to reconnect." else "Pairing saved. Enable Bluetooth on comma and choose Bluetooth only to connect.") }
            } catch (e: Exception) { runOnUiThread { message(e.message ?: "Pairing failed") } }
        }.start()
    }
    private fun connectBluetooth() {
        stopDiscovery()
        connectionStatus = null
        val key = pairing.load()
        if (key == null) { disconnected(); message("Pair Bluetooth using Galaxy Wi-Fi or LAN first, or paste an existing pairing code."); return }
        val permissions = if (Build.VERSION.SDK_INT >= 31) arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
            else arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        if (permissions.any { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }) { requestPermissions(permissions, 2); return }
        val generation = connectionGeneration.incrementAndGet()
        ble?.close()
        web?.destroy(); web = null
        Networks.manager(this).bindProcessToNetwork(null)
        val panel = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(40, 100, 40, 40) }
        panel.addView(TextView(this).apply { text = "Connecting to Galaxy Bluetooth…"; textSize = 22f })
        panel.addView(Button(this).apply { text = "Connections"; setOnClickListener { connections() } })
        setContentView(panel)
        Thread {
            val transport = BleTransport(this, key)
            if (generation != connectionGeneration.get()) { transport.close(); return@Thread }
            ble = transport
            try {
                transport.connect()
                runOnUiThread { if (!isFinishing && generation == connectionGeneration.get()) showBluetooth(transport) else transport.close() }
            } catch (e: Exception) {
                transport.close()
                runOnUiThread { if (!isFinishing && generation == connectionGeneration.get()) { disconnected(); message(e.message ?: "Bluetooth connection failed") } }
            }
        }.start()
    }
    override fun onRequestPermissionsResult(code: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(code, permissions, results)
        if (code == 2) { if (results.isNotEmpty() && results.all { it == PackageManager.PERMISSION_GRANTED }) connectBluetooth()
            else { disconnected(); message("Bluetooth access is needed for Bluetooth connections. Wi-Fi and LAN remain available.") } }
    }
    private fun showBluetooth(transport: BleTransport) {
        bluetoothMode = true
        origin = cachedOrigin
        val view = WebView(this); web = view
        view.setBackgroundColor(Color.rgb(7, 7, 18))
        view.settings.javaScriptEnabled = true; view.settings.domStorageEnabled = true
        view.settings.allowFileAccess = false; view.settings.allowContentAccess = false
        view.settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        view.addJavascriptInterface(Bridge(), "StarPilotApp")
        view.addJavascriptInterface(object {
            @JavascriptInterface fun cancel(id: String) { jobs.remove(id)?.cancel(false); worker.purge() }
            @JavascriptInterface fun request(id: String, raw: String) {
                if (id.length > 20 || raw.length > 1500000 || web !== view) return
                fun reply(value: JSONObject) { runOnUiThread {
                    if (web === view) view.evaluateJavascript("window.__galaxyBleReply(${JSONObject.quote(id)},${value});", null)
                } }
                val task = FutureTask<Unit> {
                    try {
                        if (web !== view) return@FutureTask
                        val input = JSONObject(raw)
                        val path = input.getString("path")
                        require(path.startsWith("/api/") && !path.contains('\\') && !path.contains("..") && !path.contains("//"))
                        reply(transport.request(input))
                    } catch (e: Exception) { reply(JSONObject().put("error", e.message ?: "Bluetooth failed; check the result before retrying changes.")) }
                    finally { jobs.remove(id) }
                }
                jobs[id] = task
                try { worker.execute(task) } catch (_: RejectedExecutionException) { jobs.remove(id); reply(JSONObject().put("error", "Bluetooth is busy. Wait for the current request.")) }
            }
        }, "StarPilotBLE")
        view.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(v: WebView, r: WebResourceRequest) = r.url.scheme != "https" || r.url.host != "galaxy-app.invalid"
            override fun shouldInterceptRequest(v: WebView, r: WebResourceRequest): WebResourceResponse {
                fun response(type: String, data: ByteArray, status: Int = 200) = WebResourceResponse(type, "UTF-8", status, if (status == 200) "OK" else "Unavailable", mapOf("Cache-Control" to "no-store"), ByteArrayInputStream(data))
                if (r.url.scheme != "https" || r.url.host != "galaxy-app.invalid" || r.url.port != -1) return response("text/plain", byteArrayOf(), 403)
                val path = r.url.path ?: "/"
                if (path.startsWith("/api/")) return response("application/json", "{\"error\":\"Media and direct downloads require Wi-Fi or LAN\"}".toByteArray(), 501)
                if (path.contains("..") || path.contains('\\') || path.contains("//")) return response("text/plain", byteArrayOf(), 403)
                return try {
                    var data = when (path) {
                        "/data/runtime.json" -> "{\"schemaVersion\":1,\"monitor\":\"local\"}".toByteArray()
                        "/bluetooth-fetch.js" -> assets.open("bluetooth-fetch.js").use { it.readBytes() }
                        else -> assets.open("galaxy/" + if (path == "/") "index.html" else path.removePrefix("/")).use { it.readBytes() }
                    }
                    if (path == "/" || path == "/index.html") data = String(data).replace("<head>", "<head><script src=\"/bluetooth-fetch.js\"></script>").toByteArray()
                    val type = when {
                        path == "/" || path.endsWith(".html") -> "text/html"
                        path.endsWith(".js") -> "text/javascript"
                        path.endsWith(".css") -> "text/css"
                        path.endsWith(".json") -> "application/json"
                        path.endsWith(".svg") -> "image/svg+xml"
                        else -> java.net.URLConnection.guessContentTypeFromName(path) ?: "application/octet-stream"
                    }
                    response(type, data)
                } catch (_: Exception) { response("text/plain", byteArrayOf(), 404) }
            }
            override fun onPageFinished(v: WebView, url: String) { if (web === v) share = null }
        }
        showWeb(view, "Bluetooth · controls only")
        view.loadUrl(if (share != null) "$origin/?share=${Uri.encode(share)}#/navigation" else "$origin/#/galaxy")
    }
    inner class Bridge {
        @JavascriptInterface fun bluetooth() = bluetoothMode
        @JavascriptInterface fun connectionOptions() { runOnUiThread { connections() } }
        @JavascriptInterface fun version() = BuildConfig.VERSION_NAME
        @JavascriptInterface fun uplinkState() = JSONObject().put("enabled", prefs.getBoolean("enabled", false)).put("autoStart", prefs.getBoolean("autoStart", false))
            .put("bytes", if (prefs.getString("day", "") == java.time.LocalDate.now().toString()) prefs.getLong("bytes", 0) else 0).toString()
        @JavascriptInterface fun setUplinkEnabled(enabled: Boolean) { runOnUiThread {
            prefs.edit().putBoolean("enabled", enabled).apply()
            if (enabled) startForegroundService(Intent(this@MainActivity, UplinkService::class.java))
            else stopService(Intent(this@MainActivity, UplinkService::class.java))
        } }
        @JavascriptInterface fun setAutoStart(enabled: Boolean) { prefs.edit().putBoolean("autoStart", enabled).apply() }
        @JavascriptInterface fun openWifiSettings() { runOnUiThread { startActivity(Intent(Settings.ACTION_WIFI_SETTINGS)) } }
    }
    @Deprecated("Legacy back handling") override fun onBackPressed() { if (web?.canGoBack() == true) web?.goBack() else super.onBackPressed() }
    override fun onResume() { super.onResume(); recovery.resumed() }
    override fun onStop() {
        recovery.stopped(if (discovery != null || lanPicker != null) discoveryAutomatic else null, web == null && ble == null)
        super.onStop()
    }
    override fun onDestroy() {
        stopDiscovery()
        connectionGeneration.incrementAndGet(); ble?.close(); worker.shutdownNow()
        web?.destroy(); Networks.manager(this).bindProcessToNetwork(null); super.onDestroy()
    }
}
