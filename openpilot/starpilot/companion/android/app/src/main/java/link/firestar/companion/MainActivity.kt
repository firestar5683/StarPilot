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
import android.net.ConnectivityManager
import android.net.LinkProperties
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.ViewGroup
import android.webkit.*
import android.widget.*
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.net.Inet4Address

class MainActivity : Activity() {
    @Volatile private var web: WebView? = null
    private var ble: BleTransport? = null
    private val connectionGeneration = AtomicInteger()
    @Volatile private var bluetoothMode = false
    private val pairing by lazy { PairingStore(this) }
    private val jobs = ConcurrentHashMap<String, FutureTask<Unit>>()
    private val worker = ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, ArrayBlockingQueue(16))
    private val cachedOrigin = "https://galaxy-app.invalid"
    private var screen: ConnectScreen? = null
    private val recovery = ConnectionRecovery({ discoverLan(it) }, { connect() }, { stopDiscovery() })
    private val handler = Handler(Looper.getMainLooper())
    private var pageWatchdog: Runnable? = null
    private var resumed = false
    private val knownWifi = mutableSetOf<Network>()
    private val wifiWatcher = object : ConnectivityManager.NetworkCallback() {
        override fun onLinkPropertiesChanged(network: Network, properties: LinkProperties) {
            if (network in knownWifi || properties.linkAddresses.none { it.address is Inet4Address && it.address.isSiteLocalAddress }) return
            knownWifi.add(network)
            // Open Galaxy as soon as the phone joins a Wi-Fi network, without waiting for "Try again".
            handler.postDelayed({ if (idle()) connect() }, 600)
        }
        override fun onLost(network: Network) { knownWifi.remove(network) }
    }

    private var origin = Networks.ORIGIN
    private var share: String? = null
    private val prefs by lazy { getSharedPreferences("companion", MODE_PRIVATE) }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        share = intent.getStringExtra("share")?.take(8192)
        AppUpdates.initialize(this)
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED &&
            !prefs.getBoolean("notificationPermissionRequested", false)) {
            prefs.edit().putBoolean("notificationPermissionRequested", true).apply()
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        val cm = Networks.manager(this)
        knownWifi.addAll(cm.allNetworks.filter { cm.getNetworkCapabilities(it)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true })
        // Galaxy Wi-Fi may have no internet, so do not require that capability.
        runCatching { cm.registerNetworkCallback(NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET).build(), wifiWatcher, handler) }
        connect(Networks.localOrigin(intent.getStringExtra(AppUpdates.ORIGIN_EXTRA) ?: ""))
    }
    private fun idle() = resumed && !isFinishing && web == null && ble == null && discovery == null && lanPicker == null && screen?.busy() == false
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        share = intent.getStringExtra("share")?.take(8192)
        connect(Networks.localOrigin(intent.getStringExtra(AppUpdates.ORIGIN_EXTRA) ?: ""))
    }
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
            if (!bluetoothFallback()) disconnected()
            return
        }
        val saved = Networks.localOrigin(prefs.getString("host", "") ?: "")
        if (host == null && Networks.wifi(this) == null && (saved == null || saved == Networks.ORIGIN)) {
            disconnected(); discoverLan(automatic = true); return
        }
        origin = host?.let { Networks.localOrigin(it) } ?: if (Networks.wifi(this) != null) Networks.ORIGIN else
            Networks.localOrigin(prefs.getString("host", Networks.ORIGIN)!!) ?: Networks.ORIGIN
        Networks.manager(this).bindProcessToNetwork(wifi.first)
        web?.destroy(); web = null
        clearWatchdog()
        val route = if (origin == Networks.ORIGIN) Route.GALAXY_WIFI else Route.HOME_NETWORK
        connectScreen().apply {
            refreshRoutes(this)
            headline("Opening Galaxy")
            if (route == Route.GALAXY_WIFI) { route(route, RouteState.TRYING, "Opening…"); detail("Joined the comma's Wi-Fi.") }
            else { route(route, RouteState.TRYING, "Opening ${address(origin)}…"); detail("Reaching comma on this Wi-Fi network.") }
        }
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
                if (web === v && request.isForMainFrame) runOnUiThread { pageFailed(v, host) }
            }
            // Reveal as soon as Galaxy starts drawing, so a slow asset never trips the watchdog.
            override fun onPageCommitVisible(v: WebView, url: String) { if (web === v && Networks.localOrigin(url) == origin) revealWeb() }
            override fun onPageFinished(v: WebView, url: String) {
                if (web === v && Networks.localOrigin(url) == origin) {
                    prefs.edit().putString("host", origin).apply(); share = null; revealWeb()
                    AppUpdates.checkAsync(this@MainActivity)
                }
            }
        }
        view.setDownloadListener { url, _, _, _, _ ->
            if (Networks.localOrigin(url) == origin) startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        }
        showWeb(view, route, if (route == Route.GALAXY_WIFI) "Galaxy Wi-Fi" else "Home network, ${address(origin)}", waitForPage = true)
        // A comma that vanished mid-load can leave the page pending for a long time.
        pageWatchdog = Runnable { if (web === view && screen != null) pageFailed(view, host) }.also { handler.postDelayed(it, 15000) }
        view.loadUrl(if (share != null) "$origin/?share=${Uri.encode(share)}#/navigation" else "$origin/#/galaxy")
        if (prefs.getBoolean("enabled", false)) startForegroundService(Intent(this, UplinkService::class.java))
    }
    private fun address(origin: String) = origin.removePrefix("http://").removeSuffix(":8082")
    private fun clearWatchdog() { pageWatchdog?.let { handler.removeCallbacks(it) }; pageWatchdog = null }
    private fun pageFailed(v: WebView, host: String?) {
        if (web !== v) return
        val failed = origin
        disconnected().apply {
            if (failed == Networks.ORIGIN) {
                route(Route.GALAXY_WIFI, RouteState.FAILED, "Galaxy didn't open")
                detail("This phone is on the comma's Wi-Fi, but Galaxy didn't answer. Check that Galaxy is turned on in comma settings.")
            } else {
                route(Route.HOME_NETWORK, RouteState.FAILED, "No answer at ${address(failed)}")
                detail("comma didn't answer at ${address(failed)}. Its address may have changed, or comma is off this network.")
            }
        }
        if (host == null && Networks.wifi(this) == null && Networks.wifi(this, false) != null) discoverLan(automatic = true)
        else bluetoothFallback()
    }
    private fun disconnected(): ConnectScreen {
        stopDiscovery(); clearWatchdog()
        Networks.manager(this).bindProcessToNetwork(null)
        connectionGeneration.incrementAndGet(); ble?.close(); ble = null
        val previous = web; web = null
        previous?.removeJavascriptInterface("StarPilotApp"); previous?.stopLoading(); previous?.destroy()
        screen = null
        return connectScreen().apply {
            headline("Connect to comma")
            detail("Join the comma's Galaxy Wi-Fi, or put this phone on the same Wi-Fi as comma. Galaxy opens as soon as you join.")
        }
    }
    /** The current connect screen, shown on its own; a new one if a page is showing. */
    private fun connectScreen(): ConnectScreen {
        val existing = screen
        if (existing != null) {
            val parent = existing.view.parent as? ViewGroup
            if (parent == null || parent.id != android.R.id.content) { parent?.removeView(existing.view); setContentView(existing.view) }
            return existing
        }
        val created = ConnectScreen(this, ::tryRoute, { connect() }, { startActivity(Intent(Settings.ACTION_WIFI_SETTINGS)) }, ::openTypedAddress, ::connections)
        screen = created
        refreshRoutes(created)
        setContentView(created.view)
        return created
    }
    private fun refreshRoutes(s: ConnectScreen) {
        val hotspot = Networks.wifi(this) != null
        val lan = !hotspot && Networks.wifi(this, false) != null
        val saved = Networks.localOrigin(prefs.getString("host", "") ?: "")?.takeIf { it != Networks.ORIGIN }
        val paired = pairing.load() != null
        s.mode(prefs.getString("transport", "auto"))
        s.route(Route.GALAXY_WIFI, if (hotspot) RouteState.IDLE else RouteState.UNAVAILABLE, if (hotspot) "Joined" else "Not joined")
        s.route(Route.HOME_NETWORK, if (lan) RouteState.IDLE else RouteState.UNAVAILABLE, when {
            hotspot -> "Not needed on Galaxy Wi-Fi"
            !lan -> "Not on Wi-Fi"
            saved != null -> "Last found at ${address(saved)}"
            else -> "Tap to search"
        })
        s.route(Route.BLUETOOTH, if (paired) RouteState.IDLE else RouteState.UNAVAILABLE, if (paired) "Paired, controls only" else "Not paired")
    }
    private fun tryRoute(route: Route) {
        when (route) {
            Route.GALAXY_WIFI -> if (Networks.wifi(this) != null) connect(Networks.ORIGIN) else joinWifi("Join the comma's Galaxy Wi-Fi, then come back")
            Route.HOME_NETWORK -> if (Networks.wifi(this, false) != null) discoverLan() else joinWifi("Join the same Wi-Fi as comma, then come back")
            Route.BLUETOOTH -> if (pairing.load() != null) connectBluetooth() else pairOverWifi(false)
        }
    }
    private fun joinWifi(hint: String) {
        Toast.makeText(this, hint, Toast.LENGTH_LONG).show()
        startActivity(Intent(Settings.ACTION_WIFI_SETTINGS))
    }
    private fun openTypedAddress(value: String): String? {
        val host = Networks.localOrigin(Networks.typedAddress(value)) ?: return "Use comma's private IPv4 address, like 192.168.1.10"
        connect(host); return null
    }
    private fun showWeb(view: WebView, route: Route, label: String, waitForPage: Boolean) {
        view.setOnApplyWindowInsetsListener { v, insets ->
            v.setPadding(insets.systemWindowInsetLeft, 0, insets.systemWindowInsetRight, insets.systemWindowInsetBottom); insets
        }
        val panel = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(Palette.SPACE) }
        panel.addView(ConnectScreen.webBar(this, route, label) { connections() })
        panel.addView(view, LinearLayout.LayoutParams(-1, 0, 1f))
        val overlay = screen
        if (!waitForPage || overlay == null) { screen = null; setContentView(panel); return }
        // Keep the connect screen over the page until it has loaded, instead of a blank WebView.
        (overlay.view.parent as? ViewGroup)?.removeView(overlay.view)
        setContentView(FrameLayout(this).apply { addView(panel, -1, -1); addView(overlay.view, -1, -1) })
    }
    private fun revealWeb() {
        clearWatchdog()
        val overlay = screen ?: return
        screen = null
        overlay.dismiss()
    }
    private fun message(text: String) { if (isFinishing || isDestroyed) return; AlertDialog.Builder(this).setMessage(text).setPositiveButton("OK", null).show() }
    private fun connections() {
        val options = arrayOf("Automatic (Wi-Fi first)", "Galaxy Wi-Fi / LAN only", "Bluetooth only", "Enter LAN address", "Pair Bluetooth using Wi-Fi / LAN", "Paste Bluetooth pairing code", "Forget Bluetooth on this phone", "Revoke all paired phones on comma", "Find Galaxy on LAN", "App notification settings")
        AlertDialog.Builder(this).setTitle("Galaxy connection").setItems(options) { _, which ->
            when (which) {
                0, 1, 2 -> { prefs.edit().putString("transport", arrayOf("auto", "wifi", "bluetooth")[which]).apply(); connect() }
                3 -> {
                    val field = EditText(this).apply { setText(prefs.getString("host", Networks.ORIGIN)); setSingleLine() }
                    AlertDialog.Builder(this).setTitle("Local Galaxy address").setView(field).setPositiveButton("Connect") { _, _ ->
                        val host = Networks.localOrigin(Networks.typedAddress(field.text.toString()))
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
                8 -> discoverLan(fromMenu = true)
                9 -> startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName))
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
    private fun bluetoothFallback(): Boolean {
        if (prefs.getString("transport", "auto") != "auto" || pairing.load() == null) return false
        connectBluetooth(); return true
    }
    /** [fromMenu] keeps the old menu behaviour: always confirm the address, then stay on Wi-Fi/LAN. */
    private fun discoverLan(automatic: Boolean = false, fromMenu: Boolean = false) {
        val wifi = Networks.wifi(this, false)
        if (wifi == null) {
            val text = "Join the same Wi-Fi network as comma first."
            screen?.route(Route.HOME_NETWORK, RouteState.UNAVAILABLE, "Not on Wi-Fi")
            if (automatic && bluetoothFallback()) return
            screen?.detail(text) ?: message(text)
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
                    if (fromMenu) edit.putString("transport", "wifi")
                    edit.apply(); connect(host)
                }
                fun cancel() {
                    if (generation != connectionGeneration.get() || web != null || ble != null) return
                    screen?.route(Route.HOME_NETWORK, RouteState.IDLE, "Tap to search again")
                    if (automatic) bluetoothFallback()
                }
                val s = screen
                if (hosts.isEmpty()) {
                    val text = error ?: "No comma answered on this Wi-Fi. Check that Galaxy is on and comma is on the same network. " +
                        "A new install needs a few minutes parked with internet before comma can be found. " +
                        "If your router blocks discovery, type comma's address instead."
                    s?.route(Route.HOME_NETWORK, RouteState.FAILED, "No comma found")
                    if (!(automatic && bluetoothFallback())) {
                        if (s != null) { s.headline("Connect to comma"); s.detail(text) } else message(text)
                    }
                } else if (hosts.size == 1 && !fromMenu) select(hosts.single())
                else {
                    s?.route(Route.HOME_NETWORK, RouteState.LIVE, "${hosts.size} found")
                    s?.headline("Choose your comma")
                    val picker = AlertDialog.Builder(this).setTitle("Choose your comma on this trusted LAN")
                        .setItems(hosts.map(::address).toTypedArray()) { _, which -> if (generation == connectionGeneration.get()) select(hosts[which]) }
                        .setNegativeButton("Cancel") { _, _ -> cancel() }.setOnCancelListener { cancel() }.create()
                    picker.setOnDismissListener { if (lanPicker === picker) lanPicker = null }
                    lanPicker = picker; picker.show()
                }
            }
        }
        discovery = search
        val s = screen
        if (s != null) {
            s.headline("Finding your comma")
            s.route(Route.HOME_NETWORK, RouteState.TRYING, "Searching…")
            s.detail("Looking for comma on this Wi-Fi network. This takes up to 12 seconds.")
        } else Toast.makeText(this, "Looking for comma on LAN…", Toast.LENGTH_LONG).show()
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
        if (wifi == null) { pairingNotice("To pair Bluetooth, join the comma's Galaxy Wi-Fi or the same Wi-Fi as comma first.", false); return }
        val host = if (Networks.wifi(this) != null) Networks.ORIGIN else Networks.localOrigin(prefs.getString("host", "") ?: "")
        if (host == null) { pairingNotice("To pair Bluetooth, open Galaxy over Wi-Fi first so this phone knows comma's address.", false); return }
        if (!rotate) screen?.route(Route.BLUETOOTH, RouteState.TRYING, "Pairing…")
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
                runOnUiThread {
                    if (rotate) pairingNotice("All Bluetooth phones revoked. Pair again to reconnect.", false)
                    else if (screen != null) pairingNotice("Bluetooth is paired. When Wi-Fi isn't available, Automatic uses Bluetooth for Galaxy controls.", true)
                    else message("Pairing saved. Enable Bluetooth on comma and choose Bluetooth only to connect.")
                }
            } catch (e: Exception) { runOnUiThread { pairingNotice("Couldn't pair Bluetooth: ${e.message ?: "comma didn't answer"}. Open Galaxy over Wi-Fi, then try again.", pairing.load() != null) } }
        }.start()
    }
    /** Pairing results appear on the connect screen when it is showing, otherwise in a dialog over Galaxy. */
    private fun pairingNotice(text: String, paired: Boolean) {
        val s = screen ?: return message(text)
        s.detail(text)
        s.route(Route.BLUETOOTH, if (paired) RouteState.IDLE else RouteState.UNAVAILABLE, if (paired) "Paired, controls only" else "Not paired")
    }
    private fun connectBluetooth() {
        stopDiscovery()
        val key = pairing.load()
        if (key == null) {
            disconnected().apply {
                route(Route.BLUETOOTH, RouteState.UNAVAILABLE, "Not paired")
                detail("Pair Bluetooth first: tap Bluetooth while Galaxy is reachable over Wi-Fi, or paste a pairing code in More options.")
            }
            return
        }
        val permissions = if (Build.VERSION.SDK_INT >= 31) arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
            else arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        if (permissions.any { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }) { requestPermissions(permissions, 2); return }
        val generation = connectionGeneration.incrementAndGet()
        ble?.close()
        web?.destroy(); web = null
        Networks.manager(this).bindProcessToNetwork(null)
        clearWatchdog()
        connectScreen().apply {
            refreshRoutes(this)
            headline("Connecting over Bluetooth")
            route(Route.BLUETOOTH, RouteState.TRYING, "Connecting…")
            detail("Keep Bluetooth on for comma and this phone. Bluetooth opens Galaxy controls; maps and video need Wi-Fi.")
        }
        Thread {
            val transport = BleTransport(this, key)
            if (generation != connectionGeneration.get()) { transport.close(); return@Thread }
            ble = transport
            try {
                transport.connect()
                runOnUiThread { if (!isFinishing && generation == connectionGeneration.get()) showBluetooth(transport) else transport.close() }
            } catch (e: Exception) {
                transport.close()
                runOnUiThread {
                    if (!isFinishing && generation == connectionGeneration.get()) disconnected().apply {
                        route(Route.BLUETOOTH, RouteState.FAILED, "Didn't connect")
                        detail("Bluetooth didn't connect: ${e.message ?: "comma didn't answer"}. Check that Bluetooth is on in comma settings and comma is nearby.")
                    }
                }
            }
        }.start()
    }
    override fun onRequestPermissionsResult(code: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(code, permissions, results)
        if (code == 1 && results.firstOrNull() == PackageManager.PERMISSION_GRANTED) AppUpdates.checkAsync(this)
        if (code == 2) { if (results.isNotEmpty() && results.all { it == PackageManager.PERMISSION_GRANTED }) connectBluetooth()
            else disconnected().apply {
                route(Route.BLUETOOTH, RouteState.FAILED, "Needs permission")
                detail("Allow Nearby devices to connect over Bluetooth. Wi-Fi and LAN still work without it.")
            } }
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
                if (path.startsWith("/api/")) return response("application/json", "{\"error\":\"Media and direct downloads are not available over Bluetooth. Connect using Galaxy Wi-Fi or LAN.\",\"code\":\"bluetooth_unavailable\"}".toByteArray(), 501)
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
        showWeb(view, Route.BLUETOOTH, "Bluetooth, controls only", waitForPage = false)
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
    override fun onResume() { super.onResume(); resumed = true; recovery.resumed(); AppUpdates.checkAsync(this) }
    override fun onPause() { resumed = false; super.onPause() }
    override fun onStop() {
        recovery.stopped(if (discovery != null || lanPicker != null) discoveryAutomatic else null, web == null && ble == null)
        super.onStop()
    }
    override fun onDestroy() {
        stopDiscovery(); clearWatchdog(); handler.removeCallbacksAndMessages(null)
        runCatching { Networks.manager(this).unregisterNetworkCallback(wifiWatcher) }
        connectionGeneration.incrementAndGet(); ble?.close(); worker.shutdownNow()
        web?.destroy(); Networks.manager(this).bindProcessToNetwork(null); super.onDestroy()
    }
}
