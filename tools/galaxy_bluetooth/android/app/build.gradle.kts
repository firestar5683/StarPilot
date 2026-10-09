plugins { id("com.android.application") }
android {
    buildFeatures { buildConfig = true }
    namespace = "link.firestar.galaxybt"
    compileSdk = 36
    defaultConfig {
        applicationId = "link.firestar.galaxybt.pilot"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-pilot"
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    buildTypes { release { isMinifyEnabled = false } }
}
dependencies {
    implementation("androidx.webkit:webkit:1.14.0")
    implementation("androidx.activity:activity:1.11.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20250517")
}

// Keep one Galaxy source bundle for both platforms; Android only injects its bridge shim.
val syncGalaxyAssets by tasks.registering(Sync::class) {
    from("../../ios/GalaxyBluetooth/Resources/Web") { into("Web") }
    into(layout.buildDirectory.dir("generated/galaxyAssets"))
    doLast {
        val index = destinationDir.resolve("Web/assets/mobile/index.html")
        index.writeText(index.readText().replace("<head>", "<head>\n  <script src=\"/native-bridge.js\"></script>"))
    }
}
android.sourceSets.getByName("main").assets.srcDir(syncGalaxyAssets)

