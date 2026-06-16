from yt_dlp import YoutubeDL
import json
import re
import urllib.request


def get_playlist_videos(playlist_url):
    """
    استخراج جميع فيديوهات Playlist يوتيوب بالترتيب
    بدون تنزيل أي فيديو.
    """

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        playlist = ydl.extract_info(playlist_url, download=False)

    videos = []

    for index, video in enumerate(playlist.get("entries", []), start=1):
        video_id = video.get("id")
        title = video.get("title", "Unknown Title")

        videos.append({
            "order": index,
            "title": title,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

    return {
        "playlist_title": playlist.get("title", "Unknown Playlist"),
        "video_count": len(videos),
        "videos": videos,
    }


def get_video_direct_url(video_id):
    """
    جلب رابط مباشر للفيديو بصيغة mp4 لاستخدامه في <video> tag.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best[ext=mp4]/best",
    }

    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Try to find best mp4 format
        formats = info.get("formats", [])
        video_url = None
        for fmt in formats:
            if fmt.get("ext") == "mp4" and fmt.get("vcodec") != "none":
                video_url = fmt.get("url")
                # Prefer 720p or higher
                height = fmt.get("height", 0)
                if height and height >= 720:
                    break

        if not video_url:
            # Fallback: use any format
            video_url = info.get("url")

        return video_url
    except Exception as e:
        return None


def get_video_subtitles(video_id):
    """
    جلب الترجمة (subtitles) من فيديو يوتيوب معين.
    تُعيد قائمة من الجمل مع الوقت + نص VTT كامل.
    """
    ydl_opts = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "vtt",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }

    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return [], ""

    subtitles = info.get("subtitles", {})
    automatic_captions = info.get("automatic_captions", {})

    caption_data = None
    lang_used = "en"

    for lang in ["ar", "en", "a.ar", "a.en"]:
        if lang in subtitles:
            caption_data = subtitles[lang]
            lang_used = lang.replace("a.", "")
            break

    if not caption_data:
        for lang in ["ar", "en"]:
            key = f"a.{lang}"
            if key in automatic_captions:
                caption_data = automatic_captions[key]
                lang_used = lang
                break

    if not caption_data:
        return [], ""

    vtt_url = None
    for fmt in caption_data:
        if fmt.get("ext") == "vtt":
            vtt_url = fmt.get("url")
            break

    if not vtt_url:
        return [], ""

    try:
        with urllib.request.urlopen(vtt_url, timeout=10) as response:
            raw_text = response.read().decode("utf-8")
    except Exception:
        return [], ""

    # Generate clean VTT with proper formatting
    vtt_content = "WEBVTT\n\n"

    subtitles_list = []
    lines = raw_text.split("\n")
    current_lines = []
    current_start = None
    current_end = None
    cue_index = 1

    for line in lines:
        line = line.strip()

        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue

        if "-->" in line:
            parts = line.split(" --> ")
            if len(parts) == 2:
                if current_start is not None and current_lines:
                    text = " ".join(current_lines).strip()
                    start_str = _format_vtt_time(current_start)
                    end_str = _format_vtt_time(current_end)
                    vtt_content += f"{cue_index}\n{start_str} --> {end_str}\n{text}\n\n"
                    subtitles_list.append({
                        "start": current_start,
                        "end": current_end,
                        "text": text,
                    })
                    cue_index += 1
                current_lines = []
                current_start = _parse_vtt_time(parts[0].strip())
                current_end = _parse_vtt_time(parts[1].split()[0].strip())
            continue

        if not line or line.isdigit():
            continue

        if line.startswith("<") and line.endswith(">"):
            continue

        line = re.sub(r"<[^>]+>", "", line)
        line = line.replace("&nbsp;", " ").replace("&#39;", "'").replace("&", "&")
        if line.strip():
            current_lines.append(line.strip())

    if current_start is not None and current_lines:
        text = " ".join(current_lines).strip()
        start_str = _format_vtt_time(current_start)
        end_str = _format_vtt_time(current_end)
        vtt_content += f"{cue_index}\n{start_str} --> {end_str}\n{text}\n\n"
        subtitles_list.append({
            "start": current_start,
            "end": current_end,
            "text": text,
        })

    return subtitles_list, vtt_content


def _parse_vtt_time(time_str):
    """Convert VTT timestamp to seconds."""
    parts = time_str.replace(",", ".").split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return 0.0


def _format_vtt_time(seconds):
    """Convert seconds to VTT timestamp (HH:MM:SS.mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        url = sys.argv[1]
        data = get_playlist_videos(url)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("Usage: python service.py <youtube_playlist_url>")