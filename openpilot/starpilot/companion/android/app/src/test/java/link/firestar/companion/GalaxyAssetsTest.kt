package link.firestar.companion

import org.junit.After
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.io.IOException
import java.nio.file.Files

class GalaxyAssetsTest {
    private val root: File = Files.createTempDirectory("galaxy-assets").toFile()
    private val cache = File(root, "cache")
    private val prefs = object : GalaxyPrefs {
        val values = mutableMapOf<String, String>()
        override fun get(key: String) = values[key]
        override fun set(key: String, value: String) { values[key] = value }
    }
    private val files = mutableMapOf(
        "index.html" to "<html>Galaxy</html>", "js/boot.js" to "import './app.js'", "js/app.js" to "const galaxy = true",
        "data/catalog.json" to "{}", "sentry-push-worker.js" to "self.addEventListener('push', () => {})",
    ).mapValues { it.value.toByteArray() }.toMutableMap()

    private inner class Source(var commit: String? = "a".repeat(40)) : GalaxySource {
        var fileCalls = 0
        var corrupt = false
        var offline = false
        var tooOld = false
        override fun manifest(): GalaxySource.Listing {
            if (offline) throw IOException("offline")
            if (tooOld) throw GalaxyTooOldException()
            return GalaxySource.Listing(commit, files.map { (path, data) -> GalaxyAssetFile(path, GalaxyAssetManifest.sha256(data), data.size) })
        }
        override fun file(path: String, limit: Int): ByteArray { fileCalls++; return if (corrupt) "wrong".toByteArray() else files.getValue(path) }
    }

    private fun store() = GalaxyAssetStore(cache, prefs)

    @After fun cleanup() { root.deleteRecursively() }

    @Test fun downloadsVerifiesAndSavesPagesFromComma() {
        val store = store(); val source = Source()
        assertNull(store.readyRoot)
        assertEquals(GalaxyAssetStore.NOT_DOWNLOADED, store.status)
        store.check(source)
        val ready = store.readyRoot!!
        assertEquals("const galaxy = true", File(ready, "js/app.js").readText())
        assertEquals(5, source.fileCalls)
        assertTrue(GalaxyAssetStore.verify(ready))
        assertEquals(ready, store().readyRoot)
    }

    @Test fun refreshesWhenFilesChangeEvenIfTheCommitDoesNot() {
        val store = store(); val source = Source()
        store.check(source)
        store.check(source)
        assertEquals("Galaxy matches comma.", store.status)
        assertEquals(5, source.fileCalls)
        files["js/app.js"] = "const galaxy = 2".toByteArray()
        store.check(source)
        assertEquals(6, source.fileCalls)
        assertEquals("const galaxy = 2", File(store.readyRoot!!, "js/app.js").readText())
    }

    @Test fun customOrUnpushedBuildsWorkBecauseNothingComesFromGitHub() {
        val source = Source(commit = null)
        files["js/custom-branch-only.js"] = "export default 1".toByteArray()
        val store = store()
        store.check(source)
        assertEquals("export default 1", File(store.readyRoot!!, "js/custom-branch-only.js").readText())
        assertFalse(store.olderThan("f".repeat(40)))
    }

    @Test fun failuresKeepPreviousCopy() {
        val store = store(); val source = Source()
        store.check(source)
        val previous = store.readyRoot
        files["js/app.js"] = "changed".toByteArray(); source.corrupt = true
        store.check(source)
        assertEquals(previous, store.readyRoot)
        assertTrue(store.status.contains("verification failed"))
        source.corrupt = false; source.offline = true
        store.check(source)
        assertTrue(store.status.contains("reach comma"))
        source.offline = false; source.tooOld = true
        store.check(source)
        assertTrue(store.status.startsWith("Comma’s software is too old"))
        assertEquals(previous, store.readyRoot)
        assertEquals(listOf(previous!!.name), cache.list()!!.toList())
    }

    @Test fun nothingSavedMeansNothingToServe() {
        val store = store(); val source = Source().apply { corrupt = true }
        store.check(source)
        assertNull(store.readyRoot)
        assertTrue(store.status.endsWith("No Galaxy screens are saved yet."))
        assertEquals(emptyList<String>(), cache.list()?.toList() ?: emptyList<String>())
    }

    @Test fun noticesWhenCommaMovedOnSinceTheLastDownload() {
        val store = store()
        assertFalse(store.olderThan("b".repeat(40)))
        store.check(Source(commit = "a".repeat(40)))
        assertFalse(store.olderThan("a".repeat(40)))
        assertFalse(store.olderThan(null))
        assertTrue(store.olderThan("b".repeat(40)))
    }

    @Test fun aFailedDownloadStillLeavesTheSavedScreensOlderThanComma() {
        val store = store()
        store.check(Source(commit = "a".repeat(40)))
        files["js/app.js"] = "changed".toByteArray()
        store.check(Source(commit = "b".repeat(40)).apply { corrupt = true })
        assertTrue(store.olderThan("b".repeat(40)))
        store.check(Source(commit = "b".repeat(40)))
        assertFalse(store.olderThan("b".repeat(40)))
    }

    @Test fun tamperedSavedCopyIsNotTrusted() {
        store().check(Source())
        File(store().readyRoot!!, "js/app.js").writeText("tampered")
        assertNull(store().readyRoot)
    }

    @Test fun rejectsUnsafeOrIncompleteInventories() {
        fun manifest(vararg paths: String) = GalaxyAssetManifest(paths.map { GalaxyAssetFile(it, "0".repeat(64), 1) })
        val complete = arrayOf("index.html", "js/boot.js", "js/app.js", "data/catalog.json")
        manifest(*complete).validate()
        for (bad in listOf(manifest(*complete, "js/../x.js"), manifest(*complete, "other/x.js"), manifest(*complete, "js/a b.js"),
                           manifest("index.html", "js/app.js"), manifest(*complete, "data/runtime.json"))) {
            assertThrows(GalaxyUpdateException::class.java) { bad.validate() }
        }
    }
}
