plugins { id("com.android.application") }

android {
    namespace = "link.firestar.companion"
    compileSdk = 37
    defaultConfig {
        applicationId = "link.firestar.companion"
        minSdk = 26
        targetSdk = 35
        versionCode = 16
        versionName = "1.1.14"
    }
    signingConfigs {
        create("companion") {
            storeFile = file(System.getenv("COMPANION_KEYSTORE") ?: "${System.getProperty("user.home")}/.starpilot/companion.jks")
            storePassword = System.getenv("COMPANION_KEY_PASSWORD")
            keyAlias = "companion"
            keyPassword = System.getenv("COMPANION_KEY_PASSWORD")
        }
    }
    buildTypes { getByName("release") { signingConfig = signingConfigs.getByName("companion") } }
    buildFeatures { buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}

dependencies { testImplementation("junit:junit:4.13.2") }

// Bundle this branch's screens for BLE. Wi-Fi/LAN continue to load live screens from comma.
val bundleGalaxy = tasks.register<Sync>("bundleGalaxy") {
    from("../../../galaxy/web")
    into(layout.buildDirectory.dir("generated/galaxyAssets/galaxy"))
}
android.sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/galaxyAssets").get().asFile)
tasks.named("preBuild").configure { dependsOn(bundleGalaxy) }
