package link.firestar.companion

import android.content.Context
import android.net.Network
import org.json.JSONObject
import java.io.File
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.Callable
import java.util.concurrent.ExecutionException
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class GalaxyUpdateException(message: String) : Exception(message)

data class GalaxyAssetFile(val path: String, val sha256: String, val size: Int)

data class GalaxyAssetManifest(val files: List<GalaxyAssetFile>) {
    fun validate() {
        if (files.size !in 1..512 || files.map { it.path }.toSet().size != files.size) throw GalaxyUpdateException("Galaxy update needs a compatible app version.")
        var total = 0L
        for (file in files) {
            val parts = file.path.split('/')
            if (parts.any { it.isEmpty() || it == "." || it == ".." } ||
                !file.path.all { it in '0'..'9' || it in 'A'..'Z' || it in 'a'..'z' || it in "-./_" } ||
                !(file.path in ROOT_FILES || ROOT_DIRS.any { file.path.startsWith(it) }) ||
                file.size !in 0..MAX_FILE || !isHash(file.sha256)) throw GalaxyUpdateException("Invalid Galaxy update file.")
            total += file.size
        }
        val paths = files.map { it.path }.toSet()
        if (total > MAX_TOTAL || !paths.containsAll(REQUIRED) || paths.any { it == "data/runtime.json" || it.endsWith(".sample.json") }) {
            throw GalaxyUpdateException("Galaxy update is incomplete or too large.")
        }
    }

    fun encode() = "galaxy-assets 1\n" + files.sortedBy { it.path }.joinToString("") { "${it.sha256} ${it.size} ${it.path}\n" }

    companion object {
        const val MAX_FILE = 4 * 1024 * 1024
        const val MAX_TOTAL = 32L * 1024 * 1024
        private val ROOT_FILES = setOf("index.html", "manifest.webmanifest", "sentry-push-worker.js")
        private val ROOT_DIRS = listOf("assets/", "css/", "js/", "vendor/", "data/")
        private val REQUIRED = setOf("index.html", "js/boot.js", "js/app.js", "data/catalog.json")

        fun isHash(value: String) = value.length == 64 && value.all { it in '0'..'9' || it in 'a'..'f' }
        fun sha256(data: ByteArray) = MessageDigest.getInstance("SHA-256").digest(data).joinToString("") { "%02x".format(it) }

        fun decode(text: String): GalaxyAssetManifest? {
            val lines = text.split('\n').dropLastWhile { it.isEmpty() }
            if (lines.firstOrNull() != "galaxy-assets 1") return null
            return GalaxyAssetManifest(lines.drop(1).map { line ->
                val parts = line.split(' ')
                if (parts.size != 3) return null
                GalaxyAssetFile(parts[2], parts[0], parts[1].toIntOrNull() ?: return null)
            })
        }
    }
}

/** Comma has no page inventory endpoint: an older build that cannot share its Galaxy screens. */
class GalaxyTooOldException : Exception()

/** What comma serves: its page inventory and the pages themselves. Android implements it over LAN HTTP, tests in memory. */
interface GalaxySource {
    class Listing(val commit: String?, val files: List<GalaxyAssetFile>)
    fun manifest(): Listing
    fun file(path: String, limit: Int): ByteArray
}

interface GalaxyPrefs {
    fun get(key: String): String?
    fun set(key: String, value: String)
}

/** Keeps the Bluetooth copy of Galaxy matched to the pages comma serves, downloaded over Wi-Fi/LAN. */
class GalaxyAssetStore(private val cacheRoot: File, private val prefs: GalaxyPrefs) {
    @Volatile var status = NOT_DOWNLOADED; private set
    @Volatile var readyRoot: File? = null; private set
    @Volatile var inUseRoot: File? = null

    init {
        // Validate saved assets before trusting a previous completed update.
        prefs.get(MANIFEST_KEY)?.takeIf { GalaxyAssetManifest.isHash(it) }?.let { hash ->
            val root = File(cacheRoot, hash)
            if (verify(root)) { readyRoot = root; status = "Using Galaxy screens saved from comma." }
        }
    }

    /** True when comma now runs a different build than the one these screens came from. */
    fun olderThan(commaCommit: String?): Boolean {
        val saved = prefs.get(COMMIT_KEY)?.takeIf { it.isNotEmpty() }
        return readyRoot != null && saved != null && !commaCommit.isNullOrEmpty() && saved != commaCommit
    }

    /** Compares comma's inventory with the saved copy and downloads only what changed. Never skips on an unchanged commit. */
    fun check(source: GalaxySource) {
        status = "Checking comma for Galaxy updates…"
        var stage: File? = null
        val pool = Executors.newFixedThreadPool(4)
        try {
            val listing = source.manifest()
            val manifest = GalaxyAssetManifest(listing.files.sortedBy { it.path }).apply { validate() }
            val data = manifest.encode().toByteArray()
            val hash = GalaxyAssetManifest.sha256(data)
            val saved = readyRoot
            if (saved?.name == hash) { prefs.set(COMMIT_KEY, listing.commit ?: ""); status = "Galaxy matches comma."; return }
            cacheRoot.mkdirs()
            val staging = File(cacheRoot, "staging-" + UUID.randomUUID()).also { stage = it; it.mkdirs() }
            var done = 0
            for (batch in manifest.files.chunked(4)) {
                if (Thread.currentThread().isInterrupted) throw InterruptedException()
                val results = pool.invokeAll(batch.map { entry -> Callable {
                    fun matches(bytes: ByteArray?) = bytes != null && bytes.size == entry.size && GalaxyAssetManifest.sha256(bytes) == entry.sha256
                    val local = saved?.let { File(it, entry.path).takeIf(File::isFile)?.readBytes() }?.takeIf(::matches)
                    entry.path to (local ?: source.file(entry.path, maxOf(entry.size, 1)).also {
                        if (!matches(it)) throw GalaxyUpdateException("Galaxy update verification failed.")
                    })
                } })
                for (result in results) {
                    val (path, bytes) = try { result.get() } catch (e: ExecutionException) { throw e.cause ?: e }
                    File(staging, path).apply { parentFile?.mkdirs(); writeBytes(bytes) }
                }
                done += batch.size
                status = "Preparing Galaxy update ($done/${manifest.files.size})…"
            }
            File(staging, MANIFEST_FILE).writeBytes(data)
            val destination = File(cacheRoot, hash)
            if (destination.exists()) destination.deleteRecursively()
            if (!staging.renameTo(destination)) throw GalaxyUpdateException("Galaxy update could not be saved.")
            stage = null
            readyRoot = destination
            prefs.set(MANIFEST_KEY, hash)
            prefs.set(COMMIT_KEY, listing.commit ?: "")
            // Keep one previous version while an open WebView is still using it.
            val keep = setOfNotNull(destination.canonicalPath, saved?.canonicalPath, inUseRoot?.canonicalPath)
            cacheRoot.listFiles()?.filter { it.canonicalPath !in keep }?.forEach { it.deleteRecursively() }
            status = "Galaxy update ready. It applies when you next open Galaxy over Bluetooth."
        } catch (error: Exception) {
            stage?.deleteRecursively()
            val using = if (readyRoot == null) "No Galaxy screens are saved yet." else "Using your saved Galaxy screens."
            status = when (error) {
                is GalaxyTooOldException -> "Comma’s software is too old to share Galaxy screens; update comma. $using"
                is GalaxyUpdateException -> "${error.message} $using"
                is InterruptedException -> "Galaxy update cancelled. $using"
                is java.io.IOException -> "Couldn’t reach comma to check Galaxy updates. $using"
                else -> "Galaxy update could not be read or saved. $using"
            }
        } finally { pool.shutdownNow() }
    }

    companion object {
        const val NOT_DOWNLOADED = "Galaxy screens aren’t downloaded yet. Connect to comma over Wi-Fi once."
        const val MANIFEST_FILE = "manifest.txt"
        private const val MANIFEST_KEY = "galaxy.assets.manifest"
        private const val COMMIT_KEY = "galaxy.comma.commit"

        fun verify(root: File): Boolean {
            val data = File(root, MANIFEST_FILE).takeIf(File::isFile)?.readBytes() ?: return false
            if (GalaxyAssetManifest.sha256(data) != root.name) return false
            val manifest = GalaxyAssetManifest.decode(String(data)) ?: return false
            if (runCatching { manifest.validate() }.isFailure) return false
            return manifest.files.all { file ->
                val bytes = File(root, file.path).takeIf(File::isFile)?.readBytes() ?: return@all false
                bytes.size == file.size && GalaxyAssetManifest.sha256(bytes) == file.sha256
            }
        }
    }
}

/** Android wiring: one store per process; downloads run over the Wi-Fi/LAN network that reaches comma. */
object GalaxyUpdates {
    private val executor = Executors.newSingleThreadExecutor()
    private val checking = AtomicBoolean()

    @Volatile private var store: GalaxyAssetStore? = null

    fun store(context: Context): GalaxyAssetStore = store ?: synchronized(this) {
        store ?: run {
            val app = context.applicationContext
            val prefs = app.getSharedPreferences("companion", Context.MODE_PRIVATE)
            GalaxyAssetStore(File(app.filesDir, "galaxy-updates"), object : GalaxyPrefs {
                override fun get(key: String) = prefs.getString(key, null)
                override fun set(key: String, value: String) { prefs.edit().putString(key, value).apply() }
            }).also { store = it }
        }
    }

    /** Whether comma's build, from a Bluetooth /api/software/status read, differs from the saved screens. */
    fun olderThanComma(context: Context, status: JSONObject) =
        store(context).olderThan(status.optJSONObject("installed")?.optString("commit")?.ifEmpty { null })

    /** Wi-Fi/LAN network and comma origin, chosen like the app update check does. */
    private fun lan(context: Context): Pair<Network, String>? {
        val prefs = context.getSharedPreferences("companion", Context.MODE_PRIVATE)
        val hotspot = Networks.wifi(context)
        val wifi = hotspot ?: Networks.wifi(context, false) ?: return null
        val origin = if (hotspot != null) Networks.ORIGIN else
            Networks.localOrigin(prefs.getString("host", "") ?: "")?.takeIf { it != Networks.ORIGIN } ?: return null
        return wifi.first to origin
    }

    /** Download comma's screens from [network]/[origin] in the background. */
    fun refreshAsync(context: Context, network: Network, origin: String, done: ((String) -> Unit)? = null) {
        val app = context.applicationContext
        if (!checking.compareAndSet(false, true)) { done?.invoke(store(app).status); return }
        executor.execute {
            try {
                val store = store(app)
                store.check(CommaSource(network, origin))
                done?.invoke(store.status)
            } finally { checking.set(false) }
        }
    }

    /** For the menu: refresh when the phone can reach comma over Wi-Fi/LAN, otherwise explain. */
    fun checkAsync(context: Context, done: (String) -> Unit) {
        val reach = lan(context)
        if (reach == null) done("Join comma’s Wi-Fi or home network to refresh Galaxy screens.")
        else refreshAsync(context, reach.first, reach.second, done)
    }

    private class CommaSource(private val network: Network, private val origin: String) : GalaxySource {
        override fun manifest(): GalaxySource.Listing {
            val json = JSONObject(String(get("/api/companion/web-manifest", 1024 * 1024, 5000, inventory = true)))
            if (json.optInt("schema") != 1) throw GalaxyTooOldException()
            val array = json.getJSONArray("files")
            val files = (0 until array.length()).map { array.getJSONObject(it) }
                .map { GalaxyAssetFile(it.getString("path"), it.getString("sha256"), it.getInt("size")) }
            return GalaxySource.Listing(json.optString("commit").ifEmpty { null }, files)
        }

        override fun file(path: String, limit: Int) = get("/$path", limit, 15000)

        private fun get(path: String, limit: Int, timeout: Int, inventory: Boolean = false): ByteArray {
            val connection = network.openConnection(URL(origin + path)) as HttpURLConnection
            try {
                connection.connectTimeout = timeout; connection.readTimeout = timeout
                connection.instanceFollowRedirects = false
                // Hashes cover the file bytes as stored, so ask for them unencoded.
                connection.setRequestProperty("Accept-Encoding", "identity")
                // Older comma builds answer 401 (no session) or 404 for the inventory path.
                if (inventory && connection.responseCode in setOf(401, 404)) throw GalaxyTooOldException()
                if (connection.responseCode != 200) throw GalaxyUpdateException("Comma returned HTTP ${connection.responseCode} for Galaxy screens.")
                return connection.inputStream.use { read(it, limit) }
            } finally { connection.disconnect() }
        }

        private fun read(input: InputStream, limit: Int): ByteArray {
            val output = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) return output.toByteArray()
                if (output.size() + count > limit) throw GalaxyUpdateException("Galaxy update file was larger than expected.")
                output.write(buffer, 0, count)
            }
        }
    }
}
