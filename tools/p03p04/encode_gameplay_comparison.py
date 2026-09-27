"""Encode controlled Unity capture and research-only visual comparisons; no Unity or browser calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "docs/p03p04/unity/visual-capture"
REFERENCE = ROOT / "docs/p03p04/reference"
STANDALONE = ROOT / "docs/p03p04/unity/gameplay-combat-recovery.mp4"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def probe(path: Path) -> dict:
    result = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], text=True))
    video = next(stream for stream in result["streams"] if stream["codec_type"] == "video")
    return {"width": video["width"], "height": video["height"], "fps": video["avg_frame_rate"],
            "frames": int(video["nb_frames"]), "duration_seconds": float(result["format"]["duration"]),
            "sha256": digest(path), "bytes": path.stat().st_size, "audio": any(s["codec_type"] == "audio" for s in result["streams"])}


def comparison(name: str, original: str, offset: float, duration: float, source_range: str, label: str) -> dict:
    output = REFERENCE / name
    def line_file(suffix: str, text: str) -> str:
        path = REFERENCE / (output.stem + suffix + ".txt")
        path.write_text(text, encoding="utf-8")
        return path.relative_to(ROOT).as_posix()
    original_title = line_file("-original-title", "ORIGINAL REFERENCE")
    original_subtitle = line_file("-original-subtitle", f"Source {source_range}")
    new_title = line_file("-new-title", "RACING BOIS / CONTROLLED ARENA")
    new_subtitle = line_file("-new-subtitle", "Two riders; placed traffic; scripted inputs")
    footer_first = line_file("-footer-first", label)
    footer_second = line_file("-footer-second", "Different conditions and art stages. Visual evidence; not matched-condition parity.")
    font = "Assets/RacingBois/UI/Fonts/NotoSans-Regular.ttf"
    filters = (
        f"[0:v]fps=30,scale=640:480:force_original_aspect_ratio=decrease,pad=640:544:(ow-iw)/2:64+(480-ih)/2:color=0x131821,"
        f"drawtext=fontfile={font}:textfile={original_title}:x=14:y=10:fontsize=19:fontcolor=white,"
        f"drawtext=fontfile={font}:textfile={original_subtitle}:x=14:y=36:fontsize=17:fontcolor=white[left];"
        f"[1:v]fps=30,scale=640:480:force_original_aspect_ratio=decrease,pad=640:544:(ow-iw)/2:64+(480-ih)/2:color=0x131821,"
        f"drawtext=fontfile={font}:textfile={new_title}:x=14:y=10:fontsize=19:fontcolor=white,"
        f"drawtext=fontfile={font}:textfile={new_subtitle}:x=14:y=36:fontsize=17:fontcolor=white[right];"
        f"[left][right]hstack=inputs=2,pad=1280:612:0:0:color=0x131821,"
        f"drawtext=fontfile={font}:textfile={footer_first}:x=14:y=553:fontsize=17:fontcolor=white,"
        f"drawtext=fontfile={font}:textfile={footer_second}:x=14:y=580:fontsize=17:fontcolor=white[out]"
    )
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(offset), "-i", str(REFERENCE / original),
               "-i", str(STANDALONE), "-filter_complex", filters, "-map", "[out]", "-an", "-t", str(duration),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    run(command)
    return {"path": output.relative_to(ROOT).as_posix(), "original_clip_offset_seconds": offset,
            "original_source_range": source_range, "controlled_capture_offset_seconds": 0, "metadata": probe(output)}


def main() -> None:
    timeline_path = CAPTURE / "timeline.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8-sig"))
    rows = timeline["frames"]
    frames = sorted(CAPTURE.glob("frame-*.png"))
    if len(rows) != 360 or len(frames) != 360 or [r["frame"] for r in rows] != list(range(360)):
        raise RuntimeError("Expected exactly360 ordered frames and timeline rows")
    if any(row["tick"] != (index + 1) * 2 for index, row in enumerate(rows)):
        raise RuntimeError("Capture must step60Hz simulation at2ticks per30fps exported frame")
    run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-start_number", "0",
         "-i", str(CAPTURE / "frame-%04d.png"), "-frames:v", "360", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
         "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(STANDALONE)])
    transitions, last = [], None
    for row in rows:
        if row["mode"] != last:
            transitions.append({**row, "video_time_seconds": row["frame"] / 30, "simulation_time_seconds": row["tick"] / 60})
            last = row["mode"]
    crash = next(row for row in rows if row["mode"] == "Falling")
    restored = next(row for row in rows if row["frame"] > crash["frame"] and row["mode"] in ("Riding", "Attacking"))
    frame_hashes = "\n".join(f"{path.name}:{digest(path)}" for path in frames)
    comparisons = [
        comparison("side-by-side-recovery.mp4", "original-recovery-30m58s.mp4", 0, 12, "30:58.0 - 31:10.0",
                   "Original recovery sample about7-8s; controlled Racing Bois sample3.833s. No retiming."),
        comparison("side-by-side-combat.mp4", "original-combat-34m55s.mp4", 4.5, 2.4, "34:59.5 - 35:01.9",
                   "Original arm poses vs controlled two-player hits. Original input and damage are unobserved.")
    ]
    summary = {
        "setup": timeline["setup"], "capture_kind": "Deterministic Unity Editor render export; controlled initial arena and inputs",
        "fps": 30, "frame_count": len(frames), "duration_seconds": 12, "simulation_tick_rate": 60,
        "first_sample_tick": rows[0]["tick"], "last_sample_tick": rows[-1]["tick"], "timeline_sha256": digest(timeline_path),
        "ordered_frame_sha256_manifest_digest": hashlib.sha256(frame_hashes.encode()).hexdigest(),
        "standalone_video": {"path": STANDALONE.relative_to(ROOT).as_posix(), "metadata": probe(STANDALONE)},
        "transitions": transitions,
        "sampled_recovery": {"first_falling_frame": crash["frame"], "first_resumed_driving_frame": restored["frame"],
                             "duration_seconds": (restored["frame"] - crash["frame"]) / 30,
                             "sampling_interval_seconds": 1 / 30,
                             "maximum_rider_bike_longitudinal_separation_m": max(abs(row["bikeS"] - row["s"]) for row in rows)},
        "comparisons": comparisons,
        "limits": ["Exported30fps is not measured real-time FPS or browser performance.", "No audio exists in the PNG capture or comparison encodes.",
                   "Original scene, speed, impact and separation differ; duration difference does not certify parity.",
                   "Sampled frames bound state-transition timing to1/30s; simulation runs60Hz.",
                   "Source original clips remain research-only/gitignored and are never game assets."]
    }
    output = ROOT / "docs/p03p04/unity/visual-capture-summary.json"
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(output), "video": str(STANDALONE), "recovery_seconds": summary["sampled_recovery"]["duration_seconds"], "comparisons": comparisons}, indent=2))


if __name__ == "__main__":
    main()
