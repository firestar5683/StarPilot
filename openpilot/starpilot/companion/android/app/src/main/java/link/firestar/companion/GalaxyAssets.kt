package link.firestar.companion

import android.content.Context
import android.net.Network
import android.net.NetworkCapabilities
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
        fun sha256(data: ByteArray) = hex(MessageDigest.getInstance("SHA-256").digest(data))
        fun gitBlobSha(data: ByteArray) = hex(MessageDigest.getInstance("SHA-1").apply { update("blob ${data.size}\u0000".toByteArray()); update(data) }.digest())
        private fun hex(bytes: ByteArray) = bytes.joinToString("") { "%02x".format(it) }

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

/** The GitHub repository and commit comma is running. */
data class GalaxyTarget(val repository: String, val commit: String) {
    fun key() = "$repository@$commit"

    companion object {
        private val NAME = Regex("[A-Za-z0-9._-]{1,100}")

        fun parse(remote: String?, commit: String?): GalaxyTarget? {
            if (remote == null || commit == null || commit.length != 40 || !commit.all { it in '0'..'9' || it in 'a'..'f' }) return null
            val path = listOf("https://github.com/", "git@github.com:", "ssh://git@github.com/")
                .firstOrNull { remote.startsWith(it) }?.let { remote.removePrefix(it) } ?: return null
            val parts = path.removeSuffix("/").removeSuffix(".git").split('/')
            if (parts.size != 2 || parts.any { !NAME.matches(it) || it == "." || it == ".." }) return null
            return GalaxyTarget("${parts[0]}/${parts[1]}", commit)
        }

        fun decode(key: String?): GalaxyTarget? = key?.split('@')?.takeIf { it.size == 2 }?.let { parse("https://github.com/${it[0]}", it[1]) }
    }
}

class GalaxyMissingException : Exception()

/** Where updates come from; Android implements it over HTTPS, tests implement it in memory. */
interface GalaxySource {
    class Entry(val path: String, val sha: String, val size: Int)
    /** Throws GalaxyMissingException when the commit is not on GitHub. */
    fun tree(target: GalaxyTarget): Pair<List<Entry>, Boolean>
    fun raw(target: GalaxyTarget, path: String, limit: Int): ByteArray
}

interface GalaxyPrefs {
    fun get(key: String): String?
    fun set(key: String, value: String)
}

/** Keeps the Bluetooth copy of Galaxy matched to the build comma runs, like the iPhone app's GalaxyAssetStore. */
class GalaxyAssetStore(private val cacheRoot: File, private val prefs: GalaxyPrefs, private val bundled: (String) -> ByteArray?) {
    @Volatile var status = "Galaxy is available offline."; private set
    @Volatile var readyRoot: File? = null; private set
    @Volatile var inUseRoot: File? = null

    init {
        // Validate saved assets before trusting a previous completed update.
        prefs.get(MANIFEST_KEY)?.takeIf { GalaxyAssetManifest.isHash(it) }?.let { hash ->
            val root = File(cacheRoot, hash)
            if (verify(root)) { readyRoot = root; status = "Using saved Galaxy from GitHub." }
        }
    }

    fun check(source: GalaxySource, target: GalaxyTarget) {
        if (readyRoot != null && prefs.get(COMMIT_KEY) == target.key()) { status = "Galaxy matches comma."; return }
        status = "Checking GitHub for comma's Galaxy version…"
        var stage: File? = null
        val pool = Executors.newFixedThreadPool(4)
        try {
            val commit = target.key()
            val (entries, truncated) = source.tree(target)
            if (truncated) throw GalaxyUpdateException("Galaxy update inventory is incomplete.")
            val prefix = "$RESOURCE_PATH/"
            val inventory = entries.filter { it.path.startsWith(prefix) && !it.path.endsWith("/runtime.json") && !it.path.endsWith(".sample.json") }
                .sortedBy { it.path }
            GalaxyAssetManifest(inventory.map { GalaxyAssetFile(it.path.removePrefix(prefix), "0".repeat(64), it.size) }).validate()
            cacheRoot.mkdirs()
            val staging = File(cacheRoot, "staging-" + UUID.randomUUID()).also { stage = it; it.mkdirs() }
            val saved = readyRoot
            val verified = mutableListOf<GalaxyAssetFile>()
            for (batch in inventory.chunked(4)) {
                if (Thread.currentThread().isInterrupted) throw InterruptedException()
                val results = pool.invokeAll(batch.map { entry -> Callable {
                    val path = entry.path.removePrefix(prefix)
                    fun matches(bytes: ByteArray?) = bytes != null && bytes.size == entry.size && GalaxyAssetManifest.gitBlobSha(bytes) == entry.sha
                    val local = saved?.let { File(it, path).takeIf(File::isFile)?.readBytes() }?.takeIf(::matches)
                        ?: runCatching { bundled(path) }.getOrNull()?.takeIf(::matches)
                    path to (local ?: source.raw(target, path, maxOf(entry.size, 1)).also {
                        if (!matches(it)) throw GalaxyUpdateException("Galaxy update verification failed.")
                    })
                } })
                for (result in results) {
                    val (path, bytes) = try { result.get() } catch (e: ExecutionException) { throw e.cause ?: e }
                    File(staging, path).apply { parentFile?.mkdirs(); writeBytes(bytes) }
                    verified += GalaxyAssetFile(path, GalaxyAssetManifest.sha256(bytes), bytes.size)
                }
                status = "Preparing Galaxy update (${verified.size}/${inventory.size})…"
            }
            val manifest = GalaxyAssetManifest(verified.sortedBy { it.path }).apply { validate() }
            val data = manifest.encode().toByteArray()
            val hash = GalaxyAssetManifest.sha256(data)
            if (saved?.name == hash) {
                staging.deleteRecursively(); stage = null
                prefs.set(COMMIT_KEY, commit)
                status = "Galaxy matches comma."; return
            }
            File(staging, MANIFEST_FILE).writeBytes(data)
            val destination = File(cacheRoot, hash)
            if (destination.exists()) destination.deleteRecursively()
            if (!staging.renameTo(destination)) throw GalaxyUpdateException("Galaxy update could not be saved.")
            stage = null
            readyRoot = destination
            prefs.set(MANIFEST_KEY, hash)
            prefs.set(COMMIT_KEY, commit)
            // Keep one previous version while an open WebView is still using it.
            val keep = setOfNotNull(destination.canonicalPath, saved?.canonicalPath, inUseRoot?.canonicalPath)
            cacheRoot.listFiles()?.filter { it.canonicalPath !in keep }?.forEach { it.deleteRecursively() }
            status = "Galaxy update ready. It applies when you next open Galaxy over Bluetooth."
        } catch (error: Exception) {
            stage?.deleteRecursively()
            val using = if (readyRoot == null) "the Galaxy version included with this app" else "your saved Galaxy version"
            status = when (error) {
                is GalaxyMissingException -> "Comma's build isn't on GitHub. Using $using."
                is GalaxyUpdateException -> "${error.message} Using $using."
                is InterruptedException -> "Galaxy update cancelled. Using $using."
                is java.io.IOException -> "Couldn’t check Galaxy updates (network error). Using $using."
                else -> "Galaxy update could not be read or saved. Using $using."
            }
        } finally { pool.shutdownNow() }
    }

    companion object {
        const val RESOURCE_PATH = "openpilot/starpilot/galaxy/web"
        const val MANIFEST_FILE = "manifest.txt"
        private const val MANIFEST_KEY = "galaxy.assets.manifest"
        private const val COMMIT_KEY = "galaxy.target.commit"

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

/** Android wiring: one store per process, checks over a network with validated internet. */
object GalaxyUpdates {
    private val executor = Executors.newSingleThreadExecutor()
    private val checking = AtomicBoolean()
    private val rerun = AtomicBoolean()
    @Volatile private var store: GalaxyAssetStore? = null

    fun store(context: Context): GalaxyAssetStore = store ?: synchronized(this) {
        store ?: run {
            val app = context.applicationContext
            val prefs = app.getSharedPreferences("companion", Context.MODE_PRIVATE)
            GalaxyAssetStore(File(app.filesDir, "galaxy-updates"), object : GalaxyPrefs {
                override fun get(key: String) = prefs.getString(key, null)
                override fun set(key: String, value: String) { prefs.edit().putString(key, value).apply() }
            }) { path -> app.assets.open("galaxy/$path").use { it.readBytes() } }.also { store = it }
        }
    }

    private const val TARGET_KEY = "galaxy.target"

    /** Record what comma runs, from /api/software/status, and check for its pages. */
    fun remember(context: Context, status: JSONObject) {
        val repository = status.optJSONObject("operations")?.optString("repository")?.ifEmpty { null } ?: return
        val target = GalaxyTarget.parse("https://github.com/$repository", status.optJSONObject("installed")?.optString("commit")) ?: return
        context.getSharedPreferences("companion", Context.MODE_PRIVATE).edit().putString(TARGET_KEY, target.key()).apply()
        checkAsync(context)
    }

    fun checkAsync(context: Context, done: ((String) -> Unit)? = null) {
        val app = context.applicationContext
        if (!checking.compareAndSet(false, true)) { rerun.set(true); done?.invoke(store(app).status); return }
        executor.execute {
            try {
                val store = store(app)
                val target = GalaxyTarget.decode(app.getSharedPreferences("companion", Context.MODE_PRIVATE).getString(TARGET_KEY, null))
                val network = internet(app)
                when {
                    target == null -> done?.invoke("Connect to comma once so the app can match its Galaxy version.")
                    network == null -> done?.invoke("Couldn’t check Galaxy updates without internet on this phone.")
                    else -> { store.check(GitHubSource(network), target); done?.invoke(store.status) }
                }
            } finally {
                checking.set(false)
                // A newer target may have arrived while this check ran.
                if (rerun.getAndSet(false)) checkAsync(app)
            }
        }
    }

    private fun internet(context: Context): Network? {
        val cm = Networks.manager(context)
        return cm.allNetworks.firstOrNull { network ->
            cm.getNetworkCapabilities(network)?.let {
                it.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) && it.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            } == true
        }
    }

    private class GitHubSource(private val network: Network) : GalaxySource {
        override fun tree(target: GalaxyTarget): Pair<List<GalaxySource.Entry>, Boolean> {
            val json = JSONObject(String(get("https://api.github.com/repos/${target.repository}/git/trees/${target.commit}?recursive=1", 8 * 1024 * 1024, 8000, missing = true)))
            val tree = json.getJSONArray("tree")
            val entries = (0 until tree.length()).map { tree.getJSONObject(it) }.filter { it.optString("type") == "blob" }
                .map { GalaxySource.Entry(it.getString("path"), it.getString("sha"), it.optInt("size", -1)) }
            return entries to json.optBoolean("truncated", true)
        }

        override fun raw(target: GalaxyTarget, path: String, limit: Int) =
            get("https://raw.githubusercontent.com/${target.repository}/${target.commit}/${GalaxyAssetStore.RESOURCE_PATH}/$path", limit, 15000)

        private fun get(url: String, limit: Int, timeout: Int, missing: Boolean = false): ByteArray {
            val connection = network.openConnection(URL(url)) as HttpURLConnection
            try {
                connection.connectTimeout = timeout; connection.readTimeout = timeout
                connection.instanceFollowRedirects = false
                connection.setRequestProperty("Accept", "application/vnd.github+json")
                connection.setRequestProperty("User-Agent", "Galaxy-Android")
                if (missing && connection.responseCode in setOf(404, 422)) throw GalaxyMissingException()
                if (connection.responseCode != 200) throw GalaxyUpdateException("GitHub update check returned HTTP ${connection.responseCode}.")
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
