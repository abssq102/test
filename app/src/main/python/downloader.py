import os
import json
import yt_dlp

def download(url, folder, quality=0):
    os.makedirs(folder, exist_ok=True)
    progress_path = os.path.join(folder, "progress.json")
    def report(state, percent=0, speed=0, downloaded=0, total=0):
        with open(progress_path, "w", encoding="utf-8") as out:
            json.dump({"state": state, "percent": percent, "speed": speed or 0,
                       "downloaded": downloaded or 0, "total": total or 0}, out)
    report("extracting")
    limits = [None, 720, 480]
    limit = limits[max(0, min(int(quality), 2))]
    output = []
    def hook(data):
        if data.get("status") == "downloading":
            downloaded = data.get("downloaded_bytes") or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            report("downloading", round(downloaded * 100 / total, 1) if total else 0,
                   data.get("speed"), downloaded, total)
        elif data.get("status") == "finished":
            if data.get("filename"):
                output.append(data["filename"])
            report("processing", 100)
    opts = {
        "outtmpl": os.path.join(folder, "%(title).100B-%(id)s.%(ext)s"),
        "noplaylist": True, "restrictfilenames": True,
        "quiet": True, "no_warnings": True,
        "socket_timeout": 20, "retries": 2, "progress_hooks": [hook],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise RuntimeError("No video metadata returned")
            available = [f for f in info.get("formats", [])
                if f.get("url") and f.get("vcodec") not in (None, "none")
                and f.get("acodec") not in (None, "none")]
            if limit:
                within = [f for f in available if not f.get("height") or f["height"] <= limit]
                if within:
                    available = within
            if not available:
                raise RuntimeError("No combined audio/video stream available")
            chosen = max(available, key=lambda f: (f.get("ext") == "mp4",
                f.get("height") or 0, f.get("tbr") or 0))
            opts["format"] = chosen["format_id"]
        report("starting")
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            candidate = output[-1] if output else ydl.prepare_filename(info)
        if not os.path.isfile(candidate) or os.path.getsize(candidate) == 0:
            raise RuntimeError("Download finished but output file was not found")
        report("finished", 100, downloaded=os.path.getsize(candidate),
               total=os.path.getsize(candidate))
        return candidate
    except Exception:
        report("error")
        raise
