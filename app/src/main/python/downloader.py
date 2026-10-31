import os
import yt_dlp

def download(url, folder, quality=0):
    os.makedirs(folder, exist_ok=True)
    limits = [None, 720, 480]
    limit = limits[max(0, min(int(quality), 2))]
    options = {
        "outtmpl": os.path.join(folder, "%(title).100B-%(id)s.%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 2,
    }
    # Prefer a playable single-file stream: this build does not bundle FFmpeg.
    # Choose from actual extractor results rather than assuming formats exist.
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("No video metadata returned")
        available = [
            f for f in info.get("formats", [])
            if f.get("url") and f.get("vcodec") not in (None, "none")
            and f.get("acodec") not in (None, "none")
        ]
        if limit:
            within = [f for f in available if not f.get("height") or f["height"] <= limit]
            if within:
                available = within
        if not available:
            raise RuntimeError("No combined audio/video stream available; FFmpeg may be required")
        def rank(f):
            return (f.get("ext") == "mp4", f.get("height") or 0,
                    f.get("tbr") or 0)
        chosen = max(available, key=rank)
        options["format"] = chosen["format_id"]
    with yt_dlp.YoutubeDL(options) as ydl:
        result = ydl.extract_info(url, download=True)
        return result.get("title", "video") if result else "video"
