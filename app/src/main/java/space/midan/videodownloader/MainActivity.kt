package space.midan.videodownloader

import android.app.Activity
import android.app.DownloadManager
import android.content.Context
import android.os.Bundle
import android.os.Environment
import android.content.Intent
import android.net.Uri
import android.view.Gravity
import android.widget.*

class MainActivity : Activity() {
 override fun onCreate(savedInstanceState: Bundle?) {
  super.onCreate(savedInstanceState)
  val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(36, 60, 36, 24); gravity = Gravity.CENTER_HORIZONTAL }
  val title = TextView(this).apply { text = "VideoDownloader"; textSize = 28f }
  val info = TextView(this).apply { text = "ألصق رابط ملف فيديو مباشر (MP4 أو WebM). روابط صفحات YouTube وTikTok وX تحتاج إلى استخراج رابط الوسائط، وهو غير مدعوم في هذه النسخة الأولية."; textSize = 16f }
  val input = EditText(this).apply { hint = "https://example.com/video.mp4"; setSingleLine(false); minLines = 2 }
  val button = Button(this).apply { text = "تحميل الفيديو" }
  val status = TextView(this)
  listOf(title, info, input, button, status).forEach { box.addView(it) }
  setContentView(box)
  if (intent?.action == Intent.ACTION_SEND) input.setText(intent.getStringExtra(Intent.EXTRA_TEXT) ?: "")
  button.setOnClickListener {
   val value = input.text.toString().trim()
   val uri = runCatching { Uri.parse(value) }.getOrNull()
   if (uri == null || uri.scheme != "https" || uri.host.isNullOrBlank()) { status.text = "أدخل رابط HTTPS صالحًا"; return@setOnClickListener }
   val ext = uri.lastPathSegment?.substringAfterLast('.', "")?.lowercase()
   if (ext !in listOf("mp4", "webm", "mov", "m4v")) { status.text = "هذه النسخة تقبل روابط ملفات الفيديو المباشرة فقط"; return@setOnClickListener }
   try {
    val request = DownloadManager.Request(uri).setTitle("VideoDownloader").setDescription("Downloading video").setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED).setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "video_" + System.currentTimeMillis() + "." + ext)
    (getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager).enqueue(request)
    status.text = "بدأ التحميل، راجع التنزيلات"
   } catch (e: Exception) { status.text = "فشل بدء التحميل: " + e.message }
  }
 }
}
