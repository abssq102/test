plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}
android {
    namespace = "space.midan.videodownloader"
    compileSdk = 35
    defaultConfig {
        applicationId = "space.midan.videodownloader"
        minSdk = 26
        targetSdk = 35
        versionCode = 2
        versionName = "2.0-beta"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64") }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
chaquopy {
    defaultConfig {
        version = "3.11"
        pip { install("yt-dlp") }
    }
}
