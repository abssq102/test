import os
import yt_dlp

def download(url, folder, quality=0):
    os.makedirs(folder, exist_ok=True)
    formats = [
        "best[ext=mp4]/best",
        "best[height<=720][ext=mp4]/best[height<=720]/best",
        "best[height<=480][ext=mp4]/best[height<=480]/best",
    ]
    options = {
        "format": formats[max(0, min(int(quality), 2))],
        "outtmpl": os.path.join(folder, "%(title).100B-%(id)s.%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 2,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get("title", "video") if info else "video"
