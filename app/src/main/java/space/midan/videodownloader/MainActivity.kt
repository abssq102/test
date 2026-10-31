package space.midan.videodownloader

import android.app.Activity
import android.os.Bundle
import android.os.Environment
import android.content.Intent
import android.content.Context
import android.content.ContentValues
import android.content.ClipboardManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.provider.MediaStore
import android.view.Gravity
import android.view.View
import android.widget.*
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread
import org.json.JSONObject

class MainActivity : Activity() {
    private val bg = Color.rgb(11, 16, 30)
    private val card = Color.rgb(26, 34, 53)
    private val accent = Color.rgb(37, 211, 173)
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private fun shape(color: Int, radius: Int = 16) = GradientDrawable().apply {
        setColor(color); cornerRadius = dp(radius).toFloat()
    }
    private fun label(value: String, size: Float, color: Int = Color.WHITE, bold: Boolean = false) =
        TextView(this).apply {
            text = value; textSize = size; setTextColor(color); gravity = Gravity.CENTER
            if (bold) setTypeface(null, Typeface.BOLD)
        }
    private fun publish(file: File): Uri {
        val mime = when (file.extension.lowercase()) {
            "webm" -> "video/webm"
            "mkv" -> "video/x-matroska"
            else -> "video/mp4"
        }
        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, file.name)
            put(MediaStore.Downloads.MIME_TYPE, mime)
            put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/VideoDownloader")
            put(MediaStore.Downloads.IS_PENDING, 1)
        }
        val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: error("Could not create Downloads entry")
        try {
            contentResolver.openOutputStream(uri)?.use { output ->
                file.inputStream().use { input -> input.copyTo(output) }
            } ?: error("Could not open Downloads file")
            contentResolver.update(uri, ContentValues().apply {
                put(MediaStore.Downloads.IS_PENDING, 0)
            }, null, null)
            return uri
        } catch (e: Exception) {
            contentResolver.delete(uri, null, null)
            throw e
        }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(24))
            setBackgroundColor(bg)
        }
        val scroll = ScrollView(this).apply { isFillViewport = true }
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
        }
        panel.addView(label("VideoDownloader", 25f, Color.WHITE, true),
            LinearLayout.LayoutParams(-1, -2))
        panel.addView(label("حمّل فيديوهاتك مباشرة على جهازك", 15f,
            Color.rgb(167, 183, 204)),
            LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(8) })
        panel.addView(label("رابط الفيديو", 19f, Color.WHITE, true),
            LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(42) })
        val input = EditText(this).apply {
            hint = "الصق رابط YouTube أو TikTok أو X"
            setHintTextColor(Color.rgb(140, 155, 174))
            setTextColor(Color.WHITE)
            textSize = 14f
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = shape(card)
            inputType = android.text.InputType.TYPE_CLASS_TEXT or
                android.text.InputType.TYPE_TEXT_VARIATION_URI
        }
        panel.addView(input, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(18) })
        val paste = Button(this).apply {
            text = "لصق الرابط"; setTextColor(Color.WHITE)
            background = shape(Color.rgb(53, 66, 88))
        }
        panel.addView(paste, LinearLayout.LayoutParams(-1, dp(52)).apply { topMargin = dp(12) })
        val quality = Spinner(this)
        quality.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item,
            arrayOf("أفضل جودة متاحة بدون دمج", "حتى 720p", "حتى 480p"))
        quality.setBackgroundColor(Color.rgb(225, 232, 238))
        panel.addView(quality, LinearLayout.LayoutParams(-1, dp(54)).apply { topMargin = dp(18) })
        val download = Button(this).apply {
            text = "↓  تحميل الفيديو"; textSize = 18f
            setTextColor(bg); background = shape(accent)
        }
        panel.addView(download, LinearLayout.LayoutParams(-1, dp(58)).apply { topMargin = dp(16) })
        val progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100; progress = 0; visibility = View.GONE; isIndeterminate = true
            progressTintList = android.content.res.ColorStateList.valueOf(accent)
        }
        panel.addView(progress, LinearLayout.LayoutParams(-1, dp(12)).apply { topMargin = dp(24) })
        val status = label("جاهز لاستقبال الرابط", 15f, Color.rgb(167, 183, 204))
        panel.addView(status, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(12) })
        val open = Button(this).apply {
            text = "▶ فتح الفيديو"; visibility = View.GONE
            setTextColor(Color.WHITE); background = shape(Color.rgb(53, 66, 88))
        }
        panel.addView(open, LinearLayout.LayoutParams(-1, dp(52)).apply { topMargin = dp(16) })
        panel.addView(label("مكان الحفظ: التنزيلات / VideoDownloader", 13f,
            Color.rgb(140, 155, 174)),
            LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(26) })
        scroll.addView(panel)
        root.addView(scroll)
        setContentView(root)
        if (intent?.action == Intent.ACTION_SEND)
            input.setText(intent.getStringExtra(Intent.EXTRA_TEXT) ?: "")
        paste.setOnClickListener {
            val clip = (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).primaryClip
            if (clip != null && clip.itemCount > 0)
                input.setText(clip.getItemAt(0).coerceToText(this))
        }
        download.setOnClickListener {
            val url = input.text.toString().trim()
            if (!url.startsWith("https://") && !url.startsWith("http://")) {
                status.text = "أدخل رابط فيديو صحيحًا"; return@setOnClickListener
            }
            download.isEnabled = false
            open.visibility = View.GONE
            progress.visibility = View.VISIBLE
            progress.isIndeterminate = true
            status.text = "جارٍ استخراج معلومات الفيديو..."
            val selected = quality.selectedItemPosition
            thread {
                val active = AtomicBoolean(true)
                val folder = File(getExternalFilesDir(null), "Videos").apply { mkdirs() }
                val report = File(folder, "progress.json")
                report.delete()
                val watcher = thread {
                    while (active.get()) {
                        try {
                            if (report.exists()) {
                                val data = JSONObject(report.readText())
                                val state = data.optString("state")
                                val percent = data.optDouble("percent", 0.0)
                                val done = data.optLong("downloaded", 0L)
                                val total = data.optLong("total", 0L)
                                val speed = data.optDouble("speed", 0.0)
                                runOnUiThread {
                                    when (state) {
                                        "downloading" -> {
                                            progress.isIndeterminate = total <= 0L
                                            if (total > 0L) progress.progress = percent.toInt()
                                            val size = "%.1f".format(done / 1048576.0)
                                            val rate = if (speed > 0) " • %.1f MB/s".format(speed / 1048576.0) else ""
                                            status.text = if (total > 0L)
                                                "جارٍ التنزيل: ${percent.toInt()}% • ${size} MB${rate}"
                                            else "جارٍ التنزيل: ${size} MB${rate}"
                                        }
                                        "processing" -> {
                                            progress.isIndeterminate = true
                                            status.text = "جارٍ إنهاء الملف..."
                                        }
                                        "extracting", "starting" -> {
                                            progress.isIndeterminate = true
                                            status.text = "جارٍ تجهيز رابط الفيديو..."
                                        }
                                    }
                                }
                            }
                        } catch (_: Exception) { }
                        Thread.sleep(500)
                    }
                }
                try {
                    if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                    val path = Python.getInstance().getModule("downloader")
                        .callAttr("download", url, folder.absolutePath, selected).toString()
                    val file = File(path)
                    if (!file.isFile || file.length() <= 0L)
                        error("لم يتم العثور على ملف الفيديو")
                    runOnUiThread { status.text = "جارٍ حفظ الفيديو في التنزيلات..." }
                    val uri = publish(file)
                    file.delete()
                    runOnUiThread {
                        progress.isIndeterminate = false; progress.progress = 100
                        status.text = "✓ اكتمل التنزيل والحفظ • %.1f MB".format(
                            contentResolver.openAssetFileDescriptor(uri, "r")?.use {
                                it.length.coerceAtLeast(0) / 1048576.0
                            } ?: 0.0)
                        open.visibility = View.VISIBLE
                        open.setOnClickListener {
                            val intent = Intent(Intent.ACTION_VIEW).apply {
                                setDataAndType(uri, contentResolver.getType(uri) ?: "video/*")
                                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            }
                            try { startActivity(intent) }
                            catch (_: Exception) { Toast.makeText(this, "لا يوجد مشغل مناسب", Toast.LENGTH_LONG).show() }
                        }
                        download.isEnabled = true
                    }
                } catch (e: Exception) {
                    runOnUiThread {
                        progress.visibility = View.GONE
                        status.text = "تعذر التحميل: " + (e.message ?: "خطأ غير معروف").take(220)
                        download.isEnabled = true
                    }
                } finally {
                    active.set(false)
                    watcher.join(1500)
                }
            }
        }
    }
}
