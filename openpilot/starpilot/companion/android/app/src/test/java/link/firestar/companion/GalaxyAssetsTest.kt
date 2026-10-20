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
    private val bundled = mutableMapOf<String, ByteArray>()
    private val files = mutableMapOf(
        "index.html" to "<html>Galaxy</html>", "js/boot.js" to "import './app.js'", "js/app.js" to "const galaxy = true",
        "data/catalog.json" to "{}", "sentry-push-worker.js" to "self.addEventListener('push', () => {})",
    ).mapValues { it.value.toByteArray() }.toMutableMap()

    private var target = GalaxyTarget("firestar5683/StarPilot", "a".repeat(40))

    private inner class Source : GalaxySource {
        var rawCalls = 0
        var corrupt = false
        var truncated = false
        var offline = false
        var missing = false
        override fun tree(target: GalaxyTarget): Pair<List<GalaxySource.Entry>, Boolean> {
            if (offline) throw IOException("offline")
            if (missing) throw GalaxyMissingException()
            return entries()
        }
        private fun entries() = files.map { (path, data) ->
            GalaxySource.Entry("${GalaxyAssetStore.RESOURCE_PATH}/$path", GalaxyAssetManifest.gitBlobSha(data), data.size)
        } + GalaxySource.Entry("${GalaxyAssetStore.RESOURCE_PATH}/data/runtime.json", "0", 2) to truncated
        override fun raw(target: GalaxyTarget, path: String, limit: Int): ByteArray { rawCalls++; return if (corrupt) "wrong".toByteArray() else files.getValue(path) }
    }

    private fun store() = GalaxyAssetStore(cache, prefs) { bundled[it] }

    @After fun cleanup() { root.deleteRecursively() }

    @Test fun downloadsVerifiesAndSavesUpdate() {
        val store = store(); val source = Source()
        store.check(source, target)
        val ready = store.readyRoot!!
        assertEquals("const galaxy = true", File(ready, "js/app.js").readText())
        assertFalse(File(ready, "data/runtime.json").exists())
        assertEquals(5, source.rawCalls)
        assertTrue(GalaxyAssetStore.verify(ready))
        assertEquals(ready, store().readyRoot)
    }

    @Test fun skipsWhenCommitIsUnchangedAndReusesUnchangedFiles() {
        val store = store(); val source = Source()
        store.check(source, target)
        store.check(source, target)
        assertEquals("Galaxy matches comma.", store.status)
        assertEquals(5, source.rawCalls)
        files["js/app.js"] = "const galaxy = 2".toByteArray()
        target = target.copy(commit = "b".repeat(40))
        store.check(source, target)
        assertEquals(6, source.rawCalls)
        assertEquals("const galaxy = 2", File(store.readyRoot!!, "js/app.js").readText())
    }

    @Test fun reusesBundledFiles() {
        bundled.putAll(files)
        val source = Source()
        store().check(source, target)
        assertEquals(0, source.rawCalls)
    }

    @Test fun failuresKeepPreviousCopy() {
        val store = store(); val source = Source()
        store.check(source, target)
        val previous = store.readyRoot
        target = target.copy(commit = "c".repeat(40)); files["js/app.js"] = "changed".toByteArray(); source.corrupt = true
        store.check(source, target)
        assertEquals(previous, store.readyRoot)
        assertTrue(store.status.contains("verification failed"))
        source.corrupt = false; source.truncated = true
        store.check(source, target)
        assertEquals(previous, store.readyRoot)
        source.truncated = false; source.offline = true
        store.check(source, target)
        assertTrue(store.status.contains("network error"))
        source.offline = false; source.missing = true
        store.check(source, target)
        assertEquals("Comma's build isn't on GitHub. Using your saved Galaxy version.", store.status)
        assertEquals(previous, store.readyRoot)
        assertEquals(listOf(previous!!.name), cache.list()!!.toList())
    }

    @Test fun firstFailureFallsBackToBundledCopy() {
        val store = store(); val source = Source().apply { corrupt = true }
        store.check(source, target)
        assertNull(store.readyRoot)
        assertTrue(store.status.endsWith("Using the Galaxy version included with this app."))
    }

    @Test fun tamperedSavedCopyIsNotTrusted() {
        store().check(Source(), target)
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

    @Test fun followsTheRepositoryAndCommitCommaRuns() {
        val commit = "d".repeat(40)
        for (remote in listOf("https://github.com/dirwin31/StarPilot.git", "git@github.com:dirwin31/StarPilot.git", "https://github.com/dirwin31/StarPilot")) {
            assertEquals(GalaxyTarget("dirwin31/StarPilot", commit), GalaxyTarget.parse(remote, commit))
        }
        for (remote in listOf("https://gitlab.com/a/b.git", "https://github.com/a/../b", "https://github.com/a/b/c", "/data/openpilot")) {
            assertNull(GalaxyTarget.parse(remote, commit))
        }
        assertNull(GalaxyTarget.parse("https://github.com/a/b", "abc"))
        val target = GalaxyTarget.parse("https://github.com/dirwin31/StarPilot.git", commit)!!
        assertEquals(target, GalaxyTarget.decode(target.key()))
    }
}
