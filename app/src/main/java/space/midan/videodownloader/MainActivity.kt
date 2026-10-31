package space.midan.videodownloader

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.*
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private val bg = Color.rgb(11, 16, 30)
    private val card = Color.rgb(26, 34, 53)
    private val accent = Color.rgb(37, 211, 173)
    private fun shape(color: Int, radius: Float = 24f) = GradientDrawable().apply { setColor(color); cornerRadius = radius }
    private fun label(text: String, size: Float, color: Int = Color.WHITE, bold: Boolean = false) =
        TextView(this).apply { this.text = text; textSize = size; setTextColor(color); gravity = Gravity.CENTER; if (bold) setTypeface(null, Typeface.BOLD) }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(30, 48, 30, 30); setBackgroundColor(bg) }
        val scroll = ScrollView(this).apply { isFillViewport = true }
        val panel = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL }
        val title = label("VIDEODOWNLOADER", 25f, Color.WHITE, true)
        val subtitle = label("حمّل فيديوهاتك مباشرة على جهازك", 16f, Color.rgb(167, 183, 204))
        panel.addView(title)
        panel.addView(subtitle)
        val gap = View(this)
        panel.addView(gap, LinearLayout.LayoutParams(1, 55))
        val heading = label("رابط الفيديو", 19f, Color.WHITE, true)
        panel.addView(heading)
        val input = EditText(this).apply {
            hint = "الصق رابط YouTube أو TikTok أو X"
            setHintTextColor(Color.rgb(140, 155, 174))
            setTextColor(Color.WHITE)
            textSize = 15f
            setPadding(24, 20, 24, 20)
            background = shape(card)
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
        }
        panel.addView(input, LinearLayout.LayoutParams(-1, -2).apply { topMargin = 20 })
        val paste = Button(this).apply { text = "لصق الرابط"; setTextColor(Color.WHITE); background = shape(Color.rgb(53, 66, 88)) }
        panel.addView(paste, LinearLayout.LayoutParams(-1, 110).apply { topMargin = 14 })
        val quality = Spinner(this)
        val qualities = arrayOf("أفضل جودة متاحة بدون دمج", "حتى 720p", "حتى 480p")
        quality.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, qualities)
        quality.setBackgroundColor(Color.rgb(225, 232, 238))
        panel.addView(quality, LinearLayout.LayoutParams(-1, 105).apply { topMargin = 22 })
        val download = Button(this).apply { text = "↓  تحميل الفيديو"; textSize = 19f; setTextColor(bg); background = shape(accent) }
        panel.addView(download, LinearLayout.LayoutParams(-1, 125).apply { topMargin = 22 })
        val status = label("جاهز لاستقبال الرابط", 15f, Color.rgb(167, 183, 204))
        panel.addView(status, LinearLayout.LayoutParams(-1, -2).apply { topMargin = 28 })
        panel.addView(label("التنزيلات تحفظ في مجلد التطبيق. بعض المواقع قد تتطلب تسجيل دخول أو لا تسمح بالاستخراج.", 13f, Color.rgb(140, 155, 174)), LinearLayout.LayoutParams(-1, -2).apply { topMargin = 30 })
        scroll.addView(panel)
        root.addView(scroll)
        setContentView(root)
        if (intent?.action == Intent.ACTION_SEND) input.setText(intent.getStringExtra(Intent.EXTRA_TEXT) ?: "")
        paste.setOnClickListener {
            val clip = (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).primaryClip
            if (clip != null && clip.itemCount > 0) input.setText(clip.getItemAt(0).coerceToText(this))
        }
        download.setOnClickListener {
            val url = input.text.toString().trim()
            if (!url.startsWith("https://") && !url.startsWith("http://")) { status.text = "أدخل رابط فيديو صحيحًا"; return@setOnClickListener }
            download.isEnabled = false
            status.text = "جارٍ استخراج الفيديو وتنزيله…"
            val selected = quality.selectedItemPosition
            thread {
                try {
                    if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                    val folder = File(getExternalFilesDir(null), "Videos").apply { mkdirs() }
                    val result = Python.getInstance().getModule("downloader").callAttr("download", url, folder.absolutePath, selected).toString()
                    runOnUiThread { status.text = "اكتمل التنزيل ✓\n$result"; download.isEnabled = true }
                } catch (e: Exception) {
                    runOnUiThread { status.text = "تعذر التحميل: " + (e.message ?: "خطأ غير معروف").take(250); download.isEnabled = true }
                }
            }
        }
    }
}
