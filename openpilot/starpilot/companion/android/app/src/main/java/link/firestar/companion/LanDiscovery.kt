package link.firestar.companion

import android.content.Context
import android.net.Network
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import java.net.Inet4Address
import java.util.concurrent.Executor

/** One bounded foreground search. All callbacks and state changes run on the main thread. */
class LanDiscovery(context: Context, private val network: Network,
                   private val complete: (List<String>, String?) -> Unit) {
    companion object {
        const val SERVICE = "_sp-galaxy._tcp."
        private const val SUCCESS_SETTLE_MS = 500L
    }
    private val nsd = context.getSystemService(NsdManager::class.java)
    private val wifi = context.applicationContext.getSystemService(WifiManager::class.java)
    private val handler = Handler(Looper.getMainLooper())
    private val executor = Executor { handler.post(it) }
    private val pending = ArrayDeque<NsdServiceInfo>()
    private val seen = mutableSetOf<String>()
    private val hosts = linkedSetOf<String>()
    private var active = false
    private var discoveryRequested = false
    private var resolving: NsdManager.ResolveListener? = null
    private var lock: WifiManager.MulticastLock? = null
    private var lastError: String? = null
    private val timeout = Runnable { finish(lastError) }
    private val settle = Runnable { if (hosts.isNotEmpty() && resolving == null && pending.isEmpty()) finish(null) }

    private val listener = object : NsdManager.DiscoveryListener {
        override fun onDiscoveryStarted(type: String) {}
        override fun onDiscoveryStopped(type: String) {}
        override fun onStartDiscoveryFailed(type: String, code: Int) { handler.post {
            if (active) { discoveryRequested = false; finish("LAN discovery could not start (Android error $code).") }
        } }
        override fun onStopDiscoveryFailed(type: String, code: Int) { Log.w("GalaxyLAN", "Stop discovery failed: $code") }
        override fun onServiceLost(info: NsdServiceInfo) {}
        override fun onServiceFound(info: NsdServiceInfo) { handler.post {
            if (active && seen.add(info.serviceName)) {
                handler.removeCallbacks(settle)
                pending.addLast(info)
                resolveNext()
            }
        } }
    }

    fun start() {
        check(!active)
        active = true
        try {
            // Older Android/OEM Wi-Fi stacks filter multicast without this lock.
            lock = wifi.createMulticastLock("GalaxyLAN").apply { setReferenceCounted(false); acquire() }
            if (Build.VERSION.SDK_INT >= 33) nsd.discoverServices(SERVICE, NsdManager.PROTOCOL_DNS_SD, network, executor, listener)
            else nsd.discoverServices(SERVICE, NsdManager.PROTOCOL_DNS_SD, listener)
            discoveryRequested = true
            handler.postDelayed(timeout, 12000)
        } catch (error: RuntimeException) {
            Log.w("GalaxyLAN", "Discovery failed", error)
            finish("LAN discovery could not start. Check Wi-Fi and local network access.")
        }
    }

    private fun resolveNext() {
        if (!active || resolving != null || pending.isEmpty()) return
        val info = pending.removeFirst()
        val resolver = object : NsdManager.ResolveListener {
            override fun onResolveFailed(service: NsdServiceInfo, code: Int) { handler.post {
                if (active && resolving === this) {
                    lastError = "Comma was advertised, but its LAN address could not be resolved (Android error $code)."
                    Log.w("GalaxyLAN", "Resolve failed: $code")
                    resolving = null; resolveNext()
                }
            } }
            override fun onServiceResolved(service: NsdServiceInfo) { handler.post {
                if (active && resolving === this) {
                    val addresses = if (Build.VERSION.SDK_INT >= 34) service.hostAddresses else listOfNotNull(service.host)
                    addresses.filterIsInstance<Inet4Address>().forEach { address ->
                        Networks.localOrigin("http://${address.hostAddress}:${service.port}")?.let { hosts.add(it) }
                    }
                    resolving = null; resolveNext(); settleIfReady()
                }
            } }
        }
        resolving = resolver
        try { nsd.resolveService(info, resolver) }
        catch (error: RuntimeException) {
            Log.w("GalaxyLAN", "Resolve failed", error)
            lastError = "Comma was advertised, but Android could not resolve its LAN address."
            resolving = null; resolveNext(); settleIfReady()
        }
    }

    /** Allow a brief window for another advertised comma, without imposing the full discovery timeout. */
    private fun settleIfReady() {
        if (hosts.isEmpty() || resolving != null || pending.isNotEmpty()) return
        handler.removeCallbacks(settle)
        handler.postDelayed(settle, SUCCESS_SETTLE_MS)
    }

    private fun finish(error: String?) {
        if (!active) return
        val result = hosts.toList()
        close()
        complete(result, error)
    }

    fun close() {
        active = false
        handler.removeCallbacks(timeout)
        handler.removeCallbacks(settle)
        if (discoveryRequested) runCatching { nsd.stopServiceDiscovery(listener) }
        discoveryRequested = false
        if (Build.VERSION.SDK_INT >= 34) resolving?.let { runCatching { nsd.stopServiceResolution(it) } }
        resolving = null; pending.clear()
        lock?.let { if (it.isHeld) it.release() }; lock = null
    }
}
