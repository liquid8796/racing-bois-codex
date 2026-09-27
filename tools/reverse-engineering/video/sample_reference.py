"""Read-only reference sampling: ffprobe, watch --no-whisper, timestamp contact sheets.

No source media is modified. Outputs are restricted to the selected analysis folder.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont


def stamp(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 3600:02d}:{whole // 60 % 60:02d}:{whole % 60:02d}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--watch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timestamps", help="comma-separated seconds; default each minute + intro/outro")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(args.source)
    ], text=True))
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    duration = float(metadata["format"]["duration"])
    times = [float(x) for x in args.timestamps.split(",")] if args.timestamps else sorted(set(
        list(range(0, int(duration), 60)) + [5, 10, 15, 20, 30, 45, int(duration) - 2]
    ))
    invocation = [sys.executable, str(args.watch), str(args.source), "--detail", "transcript",
                  "--timestamps", ",".join(map(str, times)), "--max-frames", str(len(times)),
                  "--resolution", "640", "--no-whisper", "--out-dir", str(out)]
    (out / "invocation.json").write_text(json.dumps(invocation, indent=2), encoding="utf-8")
    result = subprocess.run(invocation, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (out / "watch_report.md").write_text(result.stdout, encoding="utf-8")
    (out / "watch_stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode:
        raise SystemExit(result.stderr)
    rows = []
    # Watch's human report emits HH:MM:SS/MM:SS. Our input uses integer seconds.
    for path, timestamp in re.findall(r"- `([^`]+\.jpg)` \(t=([^,]+), reason=transcript-cue\)", result.stdout):
        parts = [float(x) for x in timestamp.split(":")]
        seconds = sum(value * 60**power for power, value in enumerate(reversed(parts)))
        rows.append({"timestamp_seconds": seconds, "timestamp": stamp(seconds),
                     "path": str(Path(path).resolve()), "review_method": "chronological contact sheet"})
    (out / "frames.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    font_path = Path("C:/Windows/Fonts/consola.ttf")
    font = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default()
    for batch in range(math.ceil(len(rows) / 12)):
        selected = rows[batch*12:(batch+1)*12]
        sheet = Image.new("RGB", (1280, 3*268), "#15171a")
        draw = ImageDraw.Draw(sheet)
        for index, row in enumerate(selected):
            x, y = (index % 4)*320, (index // 4)*268
            with Image.open(row["path"]) as frame:
                sheet.paste(frame.resize((320, 240)), (x, y+28))
            draw.text((x+7, y+3), row["timestamp"], font=font, fill="white")
        sheet.save(out / f"contact_{batch+1:02d}.jpg", quality=94)
    print(json.dumps({"duration_seconds": duration, "frames": len(rows), "contact_sheets": math.ceil(len(rows)/12), "out": str(out)}))


if __name__ == "__main__":
    main()
