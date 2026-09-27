"""Local-only research clips and watch cue frames. Never copies source assets into production.

Usage (project root): python tools/p03p04/prepare_reference_clips.py
Requires ffmpeg/ffprobe and the already configured watch skill. Audio/video are never uploaded.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(r"C:\Users\Liquid\Downloads\prompt\Road Rash PC (1995) - Big Game Mode (All Levels).mp4")
WATCH = Path(r"C:\Users\Liquid\.agents\skills\watch\scripts\watch.py")
OUT = ROOT / "docs/p03p04/reference"
RANGES = [("original-recovery-30m58s", 1858, 14), ("original-combat-34m55s", 2095, 15)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stamp(seconds: float) -> str:
    return f"{int(seconds) // 60:02d}:{seconds % 60:04.1f}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source_info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(SOURCE)
    ], text=True))
    manifest = {"source": str(SOURCE), "source_sha256": sha256(SOURCE), "source_metadata": source_info,
                "purpose": "User-provided video, research-only local inspection. Not a production asset.",
                "sample_interval_seconds": .5, "clips": []}
    font = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 19)
    for name, start, duration in RANGES:
        clip = OUT / f"{name}.mp4"
        frames_out = OUT / name
        frames_out.mkdir(exist_ok=True)
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-n", "-ss", str(start), "-i", str(SOURCE),
                   "-t", str(duration), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(clip)]
        if not clip.exists():
            subprocess.run(command, check=True)
        times = [index / 2 for index in range(duration * 2)]
        watch_command = [sys.executable, str(WATCH), str(clip), "--detail", "transcript", "--timestamps",
                         ",".join(map(str, times)), "--max-frames", str(len(times)), "--resolution", "640",
                         "--no-whisper", "--out-dir", str(frames_out)]
        result = subprocess.run(watch_command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (frames_out / "watch-report.md").write_text(result.stdout, encoding="utf-8")
        (frames_out / "watch-stderr.txt").write_text(result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(result.stderr)
        frames = sorted((frames_out / "frames").glob("cue_*.jpg"))
        if len(frames) != len(times):
            raise RuntimeError(f"Expected {len(times)} cue frames, got {len(frames)}")
        frame_manifest = [{"clip_time_seconds": t, "source_time_seconds": start + t, "path": str(path)}
                          for t, path in zip(times, frames)]
        (frames_out / "frames.json").write_text(json.dumps(frame_manifest, indent=2), encoding="utf-8")
        sheets = []
        for page in range((len(frames) + 15) // 16):
            sheet = Image.new("RGB", (1280, 1104), "#14181f")
            draw = ImageDraw.Draw(sheet)
            for index, row in enumerate(frame_manifest[page * 16:(page + 1) * 16]):
                x = index % 4 * 320
                y = index // 4 * 276
                draw.text((x + 5, y + 5), f"SOURCE {stamp(row['source_time_seconds'])}", fill="white", font=font)
                with Image.open(row["path"]) as frame:
                    sheet.paste(frame.resize((320, 240)), (x, y + 36))
            path = frames_out / f"contact-{page + 1:02d}.jpg"
            sheet.save(path, quality=95)
            sheets.append(str(path))
        metadata = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(clip)], text=True))
        manifest["clips"].append({"path": str(clip), "sha256": sha256(clip), "start_seconds": start,
                                 "duration_seconds": duration, "metadata": metadata, "frame_count": len(frames),
                                 "sheets": sheets, "ffmpeg_command": command, "watch_command": watch_command})
        print(json.dumps({"clip": str(clip), "frames": len(frames), "sheets": sheets}), flush=True)
    (OUT / "reference-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
