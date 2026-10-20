#!/usr/bin/env python3
"""
make_clip.py - turn a Watch & Listen share link into an audiogram for X.

    python make_clip.py "https://seanspeer.com/media/#clip=1a2b3c4d5e~a~312~371~Title"

The link names the episode, the in and out points and the title. This looks the
episode up in data/items.json, downloads its audio, transcribes the clip with
Whisper, and renders a vertical 1080x1920 MP4: blurred artwork behind, the
artwork itself, a waveform, and captions a few words at a time.

The GitHub workflow in .github/workflows/clip.yml runs this when a "Clip:" issue
is opened, which is what the site's "Make video for X" button does. It also runs
on a laptop with ffmpeg and `pip install faster-whisper numpy`.

Adapted from the audiogram route in the standalone clipper tool.
"""

import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from build import media_id

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "clips_out"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}

# Captions shown a few words at a time read better on a phone than whole sentences.
WORDS_PER_CAPTION = 6
# Transcribe a little either side so the first and last words aren't clipped.
PAD = 2.0


def parse_link(text):
    """Pull episode id, mode, in, out and title out of a share link."""
    m = re.search(r"#clip=([^~\s]+)~([va])~([\d.]+)~([\d.]+)~?([^\s&]*)", text or "")
    if not m:
        raise SystemExit("No Watch & Listen share link found. It looks like "
                         "https://seanspeer.com/media/#clip=...")
    start, end = float(m.group(3)), float(m.group(4))
    if not 1 <= end - start <= 180:
        raise SystemExit("Clips must be between 1 second and 3 minutes long.")
    return {"id": m.group(1), "mode": m.group(2), "start": start, "end": end,
            "title": urllib.parse.unquote(m.group(5)).strip()}


def find_episode(eid):
    items = json.loads((ROOT / "data" / "items.json").read_text(encoding="utf-8"))["items"]
    for it in items:
        if media_id(it) == eid:
            return it
    raise SystemExit("That link's episode isn't in data/items.json. If it's brand new, "
                     "try again after tomorrow morning's update.")


def safe_https(url):
    """The audio address comes from a third-party feed, so check it before ffmpeg sees it."""
    u = (url or "").strip()
    p = urllib.parse.urlparse(u)
    if p.scheme != "https" or not p.netloc or any(c in u for c in "\r\n\t\"'`$;|&<> "):
        raise SystemExit("Refusing an unexpected audio address: " + u[:80])
    return u


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as fh:
        shutil.copyfileobj(r, fh, 262144)


def slugify(text, limit=40):
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:limit].strip("-") or "clip"


def ass_ts(seconds):
    cs = int(round(max(0.0, seconds) * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return "{}:{:02d}:{:02d}.{:02d}".format(h, m, s, cs)


def ass_escape(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def transcribe(audio, start, end, model_name):
    """Word-level timestamps for start-PAD..end+PAD, in episode time."""
    from faster_whisper import WhisperModel
    import wave
    import numpy as np

    lo = max(0.0, start - PAD)
    wav = audio.with_suffix(".asr.wav")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", str(lo), "-t", str(end - lo + PAD), "-i", str(audio),
                    "-ac", "1", "-ar", "16000", str(wav)], check=True)
    # Raw samples rather than a path: faster-whisper's own decoder clashes with
    # newer PyAV releases.
    with wave.open(str(wav), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    wav.unlink(missing_ok=True)

    print("Transcribing with {} ...".format(model_name))
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(samples, beam_size=5, word_timestamps=True)
    words = []
    for seg in segments:
        for w in seg.words or []:
            words.append({"start": w.start + lo, "end": w.end + lo, "text": w.word.strip()})
    return [w for w in words if w["text"]]


def captions(words, start, end):
    """Group the words inside the clip into short caption lines."""
    inside = [w for w in words if w["end"] > start + 0.05 and w["start"] < end - 0.05]
    lines, buf = [], []
    for w in inside:
        buf.append(w)
        if len(buf) >= WORDS_PER_CAPTION or re.search(r"[.?!]$", w["text"]):
            lines.append(buf)
            buf = []
    if buf:
        lines.append(buf)
    return [{"start": max(l[0]["start"], start), "end": min(l[-1]["end"], end),
             "text": " ".join(w["text"] for w in l)} for l in lines]


ASS = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},70,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,2,90,90,330,1
Style: Head,{font},44,&H00F8F3F1,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,1,0,1,3,0,8,90,90,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def render(audio, cover, lines, clip, header, font, dest):
    dur = clip["end"] - clip["start"]
    out = [ASS.format(font=font)]
    if header:
        out.append("Dialogue: 0,{},{},Head,,0,0,0,,{}\n".format(ass_ts(0), ass_ts(dur), ass_escape(header)))
    for l in lines:
        out.append("Dialogue: 0,{},{},Sub,,0,0,0,,{}\n".format(
            ass_ts(l["start"] - clip["start"]), ass_ts(l["end"] - clip["start"]), ass_escape(l["text"])))
    ass = dest.with_suffix(".ass")
    ass.write_text("".join(out), encoding="utf-8")

    # The waveform takes the site's amber, the colour of a clip's in and out points.
    # draw=full keeps it solid: the default fades quiet samples, and those faded
    # pixels came out olive green over the dark background. It is drawn at half
    # size and doubled so the lines are thick enough to read on a phone.
    if cover:
        fc = ("[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
              "boxblur=40:2,eq=brightness=-0.35:saturation=1.1[bg];"
              "[1:v]scale=780:780[cov];"
              "[0:a]showwaves=s=450x100:mode=cline:draw=full:colors=0xE8A43A:rate=30,format=rgba,"
              "scale=900:200:flags=neighbor[wav];"
              "[bg][cov]overlay=(W-w)/2:330[t1];[t1][wav]overlay=(W-w)/2:1170:format=rgb[t2];"
              "[t2]ass={}[v]").format(ass.name)
        inputs = ["-i", str(audio), "-i", str(cover)]
    else:
        fc = ("color=c=0x101C38:s=1080x1920:r=30[bg];"
              "[0:a]showwaves=s=450x120:mode=cline:draw=full:colors=0xE8A43A:rate=30,format=rgba,"
              "scale=900:240:flags=neighbor[wav];"
              "[bg][wav]overlay=(W-w)/2:800:format=rgb[t1];[t1]ass={}[v]").format(ass.name)
        inputs = ["-i", str(audio)]
    cmd = (["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(clip["start"]), "-t", str(dur)] + inputs +
           ["-filter_complex", fc, "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", dest.name])
    # Run from the output folder: ffmpeg's ass filter mangles Windows drive paths.
    subprocess.run(cmd, cwd=dest.parent, check=True)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("link", help="a share link, or text containing one")
    ap.add_argument("--model", default="small.en", help="Whisper model")
    ap.add_argument("--font", default="IBM Plex Sans")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is not installed.")
    clip = parse_link(args.link)
    ep = find_episode(clip["id"])
    if not ep.get("audio"):
        raise SystemExit("That episode has no podcast audio, so it can't become an audiogram yet.")
    if clip["mode"] == "v":
        # YouTube and podcast versions of an episode don't share a timeline.
        print("Note: this clip was marked on the video. Times may not match the "
              "podcast audio; check the first and last words below.")

    title = clip["title"] or ep["title"]
    stem = "{}-{}".format(ep.get("date", ""), slugify(title))
    work = OUT / stem
    work.mkdir(parents=True, exist_ok=True)

    audio = work / "episode.mp3"
    print("Downloading audio for: " + ep["title"])
    download(safe_https(ep["audio"]), audio)
    cover = None
    if ep.get("image", "").startswith("https://"):
        try:
            download(safe_https(ep["image"]), work / "cover.jpg")
            cover = work / "cover.jpg"
        except Exception as e:
            print("  artwork failed ({}); rendering without it".format(type(e).__name__))

    words = transcribe(audio, clip["start"], clip["end"], args.model)
    lines = captions(words, clip["start"], clip["end"])
    dest = work / (stem + ".mp4")
    print("Rendering {:.0f}s audiogram ...".format(clip["end"] - clip["start"]))
    render(audio, cover, lines, clip, ep.get("outlet", ""), args.font, dest)
    audio.unlink(missing_ok=True)

    # What the workflow reports back, so a bad cut is visible before posting.
    before = [w["text"] for w in words if w["end"] <= clip["start"] + 0.05][-6:]
    after = [w["text"] for w in words if w["start"] >= clip["end"] - 0.05][:6]
    summary = {
        "file": str(dest), "name": dest.name, "title": title, "episode": ep["title"],
        "outlet": ep.get("outlet", ""), "date": ep.get("date", ""),
        "start": clip["start"], "end": clip["end"],
        "size_mb": round(dest.stat().st_size / 1_000_000, 1),
        "first": lines[0]["text"] if lines else "", "last": lines[-1]["text"] if lines else "",
        "before": " ".join(before), "after": " ".join(after),
        "transcript": " ".join(l["text"] for l in lines),
        "episode_url": ep.get("url", ""),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nWrote {}  ({} MB)".format(dest, summary["size_mb"]))
    print("Starts: " + summary["first"])
    print("Ends:   " + summary["last"])


if __name__ == "__main__":
    sys.exit(main())
