package link.firestar.companion

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.pm.PackageManager
import java.net.HttpURLConnection
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
    private var bluetoothAttemptAutomatic = false
    private val pairing by lazy { PairingStore(this) }
    private val jobs = ConcurrentHashMap<String, FutureTask<Unit>>()
    private val probes = ConcurrentHashMap<Int, HttpURLConnection>()
    private val worker = ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, ArrayBlockingQueue(16))
    private val cachedOrigin = "https://galaxy-app.invalid"
    private var screen: ConnectScreen? = null
    private val recovery = ConnectionRecovery({ discoverLan(it) }, { connect() }, { stopDiscovery() })
    private val handler = Handler(Looper.getMainLooper())
    private var pageWatchdog: Runnable? = null
    private var pendingInstallOrigin: String? = null
    private var resumed = false
    private val knownWifi = mutableSetOf<Network>()
    private val wifiWatcher = object : ConnectivityManager.NetworkCallback() {
        override fun onLinkPropertiesChanged(network: Network, properties: LinkProperties) {
            if (network in knownWifi || properties.linkAddresses.none { it.address is Inet4Address && it.address.isSiteLocalAddress }) return
            knownWifi.add(network)
            // Open Galaxy as soon as the phone joins a Wi-Fi network, without waiting for "Try again".
            handler.post {
                val mayPreemptBluetooth = bluetoothAttemptAutomatic && screen?.state(Route.BLUETOOTH) == RouteState.TRYING
                if (idle() || mayPreemptBluetooth) connect()
            }
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
        val cm = Networks.manager(this)
        knownWifi.addAll(cm.allNetworks.filter { cm.getNetworkCapabilities(it)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true })
        // Galaxy Wi-Fi may have no internet, so do not require that capability.
        runCatching { cm.registerNetworkCallback(NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET).build(), wifiWatcher, handler) }
        connect(Networks.localOrigin(intent.getStringExtra(AppUpdates.ORIGIN_EXTRA) ?: ""))
        if (PhoneGpsService.enabled(prefs) && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            startForegroundService(Intent(this, PhoneGpsService::class.java))
        }
    }
    private fun idle() = resumed && !isFinishing && web == null && ble == null && discovery == null && lanPicker == null && screen?.busy() == false
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        share = intent.getStringExtra("share")?.take(8192)
        connect(Networks.localOrigin(intent.getStringExtra(AppUpdates.ORIGIN_EXTRA) ?: ""))
    }
    /** Invalidates every older async result before a new route is allowed to win. */
    private fun supersedeConnection(): Int {
        stopDiscovery()
        val generation = connectionGeneration.incrementAndGet()
        jobs.values.forEach { it.cancel(false) }; jobs.clear(); worker.purge()
        ble?.close(); ble = null
        bluetoothMode = false
        bluetoothAttemptAutomatic = false
        clearWatchdog()
        val previous = web; web = null
        previous?.removeJavascriptInterface("StarPilotApp"); previous?.stopLoading(); previous?.destroy()
        Networks.manager(this).bindProcessToNetwork(null)
        return generation
    }
    private fun connect(host: String? = null) {
        val generation = supersedeConnection()
        val mode = prefs.getString("transport", "auto")
        if (host == null && mode == "bluetooth") { connectBluetooth(); return }
        val hotspot = Networks.wifi(this)
        val wifi = hotspot ?: Networks.wifi(this, false)
        if (wifi == null) {
            if (!bluetoothFallback()) disconnected()
            return
        }
        val saved = Networks.localOrigin(prefs.getString("host", "") ?: "")
        if (host == null) {
            val candidate = if (hotspot != null) Networks.ORIGIN else saved?.takeIf { it != Networks.ORIGIN }
            if (candidate != null) probeWifi(wifi.first, candidate, generation)
            else {
                disconnected()
                // Give LAN discovery a short, bounded head start before Automatic falls back to Bluetooth.
                discoverLan(automatic = true)
            }
            return
        }
        val localOrigin = Networks.localOrigin(host)
        if (localOrigin == null) { disconnected(); return }
        origin = localOrigin
        Networks.manager(this).bindProcessToNetwork(wifi.first)
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
                if (web === v && request.isForMainFrame) runOnUiThread { pageFailed(v) }
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
            val uri = Uri.parse(url)
            if (Networks.localOrigin(url) == origin && uri.path in setOf("/app.apk", "/api/companion/app.apk")) {
                runOnUiThread { requestAppUpdate() }
            } else if (Networks.localOrigin(url) == origin) startActivity(Intent(Intent.ACTION_VIEW, uri))
        }
        showWeb(view, route, if (route == Route.GALAXY_WIFI) "Galaxy Wi-Fi" else "Home network, ${address(origin)}", waitForPage = true)
        // A comma that vanished mid-load can leave the page pending for a long time.
        val watchdogMs = if (route == Route.HOME_NETWORK && mode == "auto" && pairing.load() != null) 4000L else 10000L
        pageWatchdog = Runnable { if (web === view && screen != null) pageFailed(view) }.also { handler.postDelayed(it, watchdogMs) }
        view.loadUrl(if (share != null) "$origin/?share=${Uri.encode(share)}#/navigation" else "$origin/#/galaxy")
        if (prefs.getBoolean("enabled", false)) startForegroundService(Intent(this, UplinkService::class.java))
    }
    private fun probeWifi(network: Network, candidate: String, generation: Int) {
        val route = if (candidate == Networks.ORIGIN) Route.GALAXY_WIFI else Route.HOME_NETWORK
        connectScreen().apply {
            refreshRoutes(this)
            headline("Checking Wi-Fi")
            route(route, RouteState.TRYING, "Checking…")
            detail(if (route == Route.GALAXY_WIFI) "Waiting for Galaxy to answer on comma Wi-Fi."
                else "Checking the last comma address before searching this network.")
        }
        val cookie = CookieManager.getInstance().getCookie(candidate)
        Thread({
            var connection: HttpURLConnection? = null
            val reachable = GalaxyProbe.reachable(network, candidate, cookie) {
                connection = it
                probes[generation] = it
                if (generation != connectionGeneration.get()) it.disconnect()
            }
            connection?.let { probes.remove(generation, it) }
            runOnUiThread {
                if (isFinishing || isDestroyed || generation != connectionGeneration.get()) return@runOnUiThread
                if (reachable) connect(candidate)
                else if (route == Route.HOME_NETWORK) discoverLan(automatic = true)
                else if (!bluetoothFallback()) disconnected().apply {
                    route(Route.GALAXY_WIFI, RouteState.FAILED, "Galaxy didn't answer")
                    detail("This phone is on the comma's Wi-Fi, but Galaxy didn't answer.")
                }
            }
        }, "GalaxyProbe").start()
    }
    private fun address(origin: String) = origin.removePrefix("http://").removeSuffix(":8082")
    private fun clearWatchdog() { pageWatchdog?.let { handler.removeCallbacks(it) }; pageWatchdog = null }
    private fun pageFailed(v: WebView) {
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
        bluetoothFallback()
    }
    private fun disconnected(): ConnectScreen {
        supersedeConnection()
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
            Route.GALAXY_WIFI -> if (Networks.wifi(this) != null) connect(Networks.ORIGIN) else {
                supersedeConnection(); refreshRoutes(connectScreen()); joinWifi("Join the comma's Galaxy Wi-Fi, then come back")
            }
            Route.HOME_NETWORK -> {
                supersedeConnection(); refreshRoutes(connectScreen())
                if (Networks.wifi(this, false) != null) discoverLan() else joinWifi("Join the same Wi-Fi as comma, then come back")
            }
            Route.BLUETOOTH -> if (pairing.load() != null) connectBluetooth() else {
                supersedeConnection(); refreshRoutes(connectScreen()); pairPhone()
            }
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
        ConnectionSheet(this, Transport.of(prefs.getString("transport", "auto")))
            .onTransport { prefs.edit().putString("transport", it.key).apply(); connect() }
            .group("Home network") {
                action("Find comma on this network", "Search this Wi-Fi for Galaxy") { discoverLan(fromMenu = true) }
                action("Type comma's address", "For routers that block discovery") {
                    val field = EditText(this@MainActivity).apply { setText(prefs.getString("host", Networks.ORIGIN)); setSingleLine() }
                    AlertDialog.Builder(this@MainActivity).setTitle("Local Galaxy address").setView(field).setPositiveButton("Connect") { _, _ ->
                        val host = Networks.localOrigin(Networks.typedAddress(field.text.toString()))
                        if (host == null) message("Use a private IPv4 address on port 8082") else {
                            prefs.edit().putString("host", host).putString("transport", "wifi").apply(); connect(host)
                        }
                    }.setNegativeButton("Cancel", null).show()
                }
            }
            .group("Bluetooth pairing") {
                action("Pair with comma", "On comma (Settings > Bluetooth > Pair phone) or Galaxy (Bluetooth page), then tap here") { pairPhone() }
                action("Forget pairing on this phone") { pairing.forget(); ble?.close(); disconnected() }
            }
            .group("Phone GPS") {
                if (PhoneGpsService.enabled(prefs)) action("Stop sharing phone GPS") { setPhoneGps(false) }
                else action("Share phone GPS with comma", "Comma uses it for navigation when its own GPS has no fix") { setPhoneGps(true) }
            }
            .group("This app") { action("Notification settings") { appNotificationSettings() } }
            .show()
    }
    private fun appNotificationSettings() {
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED &&
            !prefs.getBoolean("notificationPermissionRequested", false)) {
            prefs.edit().putBoolean("notificationPermissionRequested", true).apply()
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        } else startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName))
    }
    private fun requestAppUpdate(requestedOrigin: String = origin) {
        val localOrigin = Networks.localOrigin(requestedOrigin)
        if (bluetoothMode || localOrigin == null) {
            message("Connect using Galaxy Wi-Fi or LAN to download the app update.")
            return
        }
        if (!packageManager.canRequestPackageInstalls()) {
            pendingInstallOrigin = localOrigin
            Toast.makeText(this, "Allow StarPilot to install its downloaded update, then return.", Toast.LENGTH_LONG).show()
            startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:$packageName")))
            return
        }
        pendingInstallOrigin = null
        val network = (if (localOrigin == Networks.ORIGIN) Networks.wifi(this) else Networks.wifi(this, false))?.first
        if (network == null) {
            message("Reconnect to the same Wi-Fi as comma, then try the update again.")
            return
        }
        if (!AppInstaller.start(this, network, localOrigin)) Toast.makeText(this, "An app update is already in progress.", Toast.LENGTH_LONG).show()
    }
    private var discovery: LanDiscovery? = null
    private var discoveryAutomatic = false
    private var lanPicker: AlertDialog? = null
    private fun stopDiscovery() {
        probes.values.forEach { it.disconnect() }; probes.clear()
        discovery?.close(); discovery = null
        lanPicker?.dismiss(); lanPicker = null
    }
    private fun bluetoothFallback(): Boolean {
        if (prefs.getString("transport", "auto") != "auto" || pairing.load() == null) return false
        connectBluetooth(automatic = true); return true
    }
    /** [fromMenu] keeps the old menu behavior: always confirm the address, then stay on Wi-Fi/LAN. */
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
        val quickBluetoothFallback = automatic && prefs.getString("transport", "auto") == "auto" && pairing.load() != null
        val search = LanDiscovery(this, wifi.first, if (quickBluetoothFallback) GalaxyProbe.AUTOMATIC_DISCOVERY_MS else 12000L) { hosts, error ->
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
            s.detail(if (quickBluetoothFallback) "Checking this Wi-Fi for comma before trying Bluetooth."
                else "Looking for comma on this Wi-Fi network. This takes up to 12 seconds.")
        } else Toast.makeText(this, "Looking for comma on LAN…", Toast.LENGTH_LONG).show()
        search.start()
    }
    private fun savePairing(value: JSONObject) {
        require(value.getString("type") == "galaxy-bluetooth" && value.getInt("version") == 1)
        val hex = value.getString("key")
        require(hex.matches(Regex("[0-9a-fA-F]{64}")))
        pairing.save(hex.chunked(2).map { it.toInt(16).toByte() }.toByteArray(), value.optString("id").ifEmpty { null })
    }
    /** How comma lists this phone under Settings → Bluetooth, e.g. "Danny's Pixel 8". */
    private fun phoneName(): String =
        (Settings.Global.getString(contentResolver, Settings.Global.DEVICE_NAME)?.trim()?.takeIf { it.isNotEmpty() }
            ?: "${Build.MANUFACTURER} ${Build.MODEL}").take(40)
    private fun phoneHello(): JSONObject = JSONObject().put("name", phoneName()).apply { pairing.previousId()?.let { put("replaces", it) } }
    /** One step for the app and music: comma's open pairing window gives this phone its key, then bonds it for music. */
    private fun pairPhone() {
        val permissions = if (Build.VERSION.SDK_INT >= 31) arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
            else arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        if (permissions.any { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }) { requestPermissions(permissions, 5); return }
        val generation = supersedeConnection()
        connectScreen().apply {
            refreshRoutes(this)
            headline("Pairing with comma")
            route(Route.BLUETOOTH, RouteState.TRYING, "Pairing…")
            detail("On comma open Settings > Bluetooth > Pair phone, or tap Pair phone on the Galaxy Bluetooth page. Keep Bluetooth on for comma and this phone.")
        }
        Thread {
            val transport = BleTransport(this, null)
            ble = transport
            try {
                val claim = ClaimPairing.claim(transport, phoneName())
                if (generation != connectionGeneration.get()) return@Thread
                pairing.save(claim.key, claim.id.ifEmpty { null })
                transport.close()
                runOnUiThread { if (generation == connectionGeneration.get()) screen?.detail("Paired. Setting up music: tap Pair if your phone asks.") }
                val outcome = bondMusic(claim.adapterAddress)
                if (generation != connectionGeneration.get()) return@Thread
                runOnUiThread {
                    if (generation != connectionGeneration.get()) return@runOnUiThread
                    MusicBond.message(outcome)?.let { message(it) }
                    connectBluetooth()
                }
            } catch (e: Exception) {
                transport.close()
                runOnUiThread { if (generation == connectionGeneration.get()) pairingNotice("Couldn't pair: ${e.message ?: "comma didn't answer"}", pairing.load() != null) }
            }
        }.start()
    }
    private fun bondMusic(address: String): MusicBond.Outcome {
        val adapter = getSystemService(android.bluetooth.BluetoothManager::class.java)?.adapter
        if (adapter == null || !adapter.isEnabled) return MusicBond.Outcome.FAILED
        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) return MusicBond.Outcome.FAILED
        return try {
            MusicBond({ adapter.bondedDevices.map { it.address.uppercase() }.toSet() }, { adapter.getRemoteDevice(it).createBond() }).run(address)
        } catch (_: Exception) { MusicBond.Outcome.FAILED }
    }
    /** Pairing results appear on the connect screen when it is showing, otherwise in a dialog over Galaxy. */
    private fun phoneGpsPermissions(): Array<String> = arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION) +
        (if (Build.VERSION.SDK_INT >= 31) arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT) else emptyArray()) +
        (if (Build.VERSION.SDK_INT >= 33) arrayOf(Manifest.permission.POST_NOTIFICATIONS) else emptyArray())
    private fun setPhoneGps(enabled: Boolean) {
        if (!enabled) { prefs.edit().putBoolean("phoneGps", false).apply(); stopService(Intent(this, PhoneGpsService::class.java)); return }
        val missing = phoneGpsPermissions().filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) { requestPermissions(missing.toTypedArray(), 4); return }
        prefs.edit().putBoolean("phoneGps", true).apply()
        startForegroundService(Intent(this, PhoneGpsService::class.java))
        message("Sharing phone GPS. Keep this app's notification while driving; comma uses it only when its own GPS has no fix.")
    }
    private fun pairingNotice(text: String, paired: Boolean) {
        val s = screen ?: return message(text)
        s.detail(text)
        s.route(Route.BLUETOOTH, if (paired) RouteState.IDLE else RouteState.UNAVAILABLE, if (paired) "Paired, controls only" else "Not paired")
    }
    private fun connectBluetooth(automatic: Boolean = false) {
        val generation = supersedeConnection()
        bluetoothAttemptAutomatic = automatic
        val key = pairing.load()
        if (key == null) {
            disconnected().apply {
                route(Route.BLUETOOTH, RouteState.UNAVAILABLE, "Not paired")
                detail("Pair first: tap Pair phone on comma (Settings > Bluetooth) or on the Galaxy Bluetooth page, then tap Pair with comma here.")
            }
            return
        }
        val permissions = if (Build.VERSION.SDK_INT >= 31) arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
            else arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        if (permissions.any { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }) { requestPermissions(permissions, 2); return }
        connectScreen().apply {
            refreshRoutes(this)
            headline("Connecting over Bluetooth")
            route(Route.BLUETOOTH, RouteState.TRYING, "Connecting…")
            detail("Keep Bluetooth on for comma and this phone. Bluetooth opens Galaxy controls; maps and video need Wi-Fi.")
        }
        Thread {
            var transport = BleTransport(this, key, phoneHello())
            if (generation != connectionGeneration.get()) { transport.close(); return@Thread }
            ble = transport
            try {
                val remembered = pairing.deviceAddress()
                val device = try { transport.connect(remembered) } catch (first: Exception) {
                    if (remembered == null || generation != connectionGeneration.get()) throw first
                    transport.close()
                    transport = BleTransport(this, key, phoneHello())
                    ble = transport
                    transport.connect()
                }
                pairing.rememberDevice(device)
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
        if (code == 5 && results.isNotEmpty() && results.all { it == PackageManager.PERMISSION_GRANTED }) pairPhone()
        if (code == 4) {
            if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                prefs.edit().putBoolean("phoneGps", true).apply()
                startForegroundService(Intent(this, PhoneGpsService::class.java))
            } else message("Allow precise location to share phone GPS with comma.")
        }
        if (code == 2) { if (results.isNotEmpty() && results.all { it == PackageManager.PERMISSION_GRANTED }) connectBluetooth(bluetoothAttemptAutomatic)
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
        @JavascriptInterface fun installUpdate() { runOnUiThread { requestAppUpdate() } }
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
    override fun onResume() {
        super.onResume(); resumed = true; recovery.resumed(); AppUpdates.checkAsync(this)
        pendingInstallOrigin?.let { if (packageManager.canRequestPackageInstalls()) requestAppUpdate(it) }
    }
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
