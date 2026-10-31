plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android { namespace = "space.midan.videodownloader"; compileSdk = 35
 defaultConfig { applicationId = "space.midan.videodownloader"; minSdk = 26; targetSdk = 35; versionCode = 1; versionName = "1.0" }
 compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
 kotlinOptions { jvmTarget = "17" }
}
