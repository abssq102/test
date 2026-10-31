import os
import json
import yt_dlp
import shutil

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
            formats = info.get("formats") or []
            combined = [f for f in formats if f.get("url")
                and f.get("vcodec") not in (None, "none")
                and f.get("acodec") not in (None, "none")]
            if limit:
                combined = [f for f in combined
                    if not f.get("height") or f["height"] <= limit]
            if combined:
                chosen = max(combined, key=lambda f: (
                    f.get("ext") == "mp4", f.get("height") or 0,
                    f.get("tbr") or 0))
                opts["format"] = chosen["format_id"]
            else:
                if not shutil.which("ffmpeg"):
                    raise RuntimeError(
                        "Separate audio/video streams require FFmpeg on device")
                ceiling = "[height<=%d]" % limit if limit else ""
                opts["format"] = "bestvideo" + ceiling + "+bestaudio/best"
                opts["merge_output_format"] = "mp4"
        report("starting")
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            candidate = ydl.prepare_filename(info)
            if opts.get("merge_output_format"):
                candidate = os.path.splitext(candidate)[0] + ".mp4"
            if not os.path.isfile(candidate) and output:
                candidate = output[-1]
        if not os.path.isfile(candidate) or os.path.getsize(candidate) == 0:
            raise RuntimeError("Download finished but output file was not found")
        report("finished", 100, downloaded=os.path.getsize(candidate),
               total=os.path.getsize(candidate))
        return candidate
    except Exception:
        report("error")
        raise
