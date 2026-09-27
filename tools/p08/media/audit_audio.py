"""Independent full decode and bounded-memory PCM/codec audit for original P08 audio."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs/p08/media"
RATE = 32000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(samples):
    samples = samples.reshape(len(samples), -1)
    peak4 = 0.0
    # A 256-sample overlap avoids false resampler block-edge transients.
    block = RATE * 4
    for start in range(0, len(samples), block):
        a, b = max(0, start - 256), min(len(samples), start + block + 256)
        up = resample_poly(samples[a:b], 4, 1, axis=0)
        low = (start - a) * 4
        high = min(start + block, len(samples)) * 4 - a * 4
        peak4 = max(peak4, float(np.max(np.abs(up[low:high]))))
    differences = np.abs(np.diff(samples, axis=0))
    rms_blocks = [float(np.sqrt(np.mean(part.astype(np.float64) ** 2))) for part in np.array_split(samples, 32) if len(part)]
    return dict(sample_peak=float(np.max(np.abs(samples))), true_peak_4x=peak4,
                rms=float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))),
                dc=float(np.max(np.abs(np.mean(samples.astype(np.float64), axis=0)))),
                clipped_samples=int(np.sum(np.abs(samples) >= .999)),
                seam=float(np.max(np.abs(samples[0] - samples[-1]))),
                edge_peak=float(max(np.max(np.abs(samples[0])), np.max(np.abs(samples[-1])))),
                adjacent_delta_p99=float(np.quantile(differences, .99)),
                rms_segments=rms_blocks, pcm_sha256=hashlib.sha256(samples.tobytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    manifest_path = REPORT / "audio-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    originals = {r["sha256"] for r in json.loads((ROOT / "docs/p08/content/reference-baseline.json").read_text(encoding="utf-8"))["data"]["manifest"]}
    checks = []
    preview = []
    for item in manifest["clips"]:
        source, runtime = ROOT / item["source"], ROOT / item["runtime"]
        with wave.open(str(source), "rb") as stream:
            channels, width, rate, frames = stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()
            raw = stream.readframes(frames)
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32).reshape(-1, channels) / 32768
        original = metrics(samples)
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(runtime), "-f", "f32le", "-acodec", "pcm_f32le", "-ar", str(RATE), "-ac", str(channels), "-"]
        result = subprocess.run(command, capture_output=True)
        if result.returncode:
            raise RuntimeError("Runtime decode failed for " + item["id"])
        decoded = np.frombuffer(result.stdout, dtype="<f4").reshape(-1, channels)
        compressed = metrics(decoded)
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration_ts,time_base", "-of", "json", str(runtime)], capture_output=True, text=True)
        if probe.returncode:
            raise RuntimeError("Runtime duration probe failed for " + item["id"])
        stream_info = json.loads(probe.stdout)["streams"][0]
        numerator, denominator = map(int, stream_info["time_base"].split("/"))
        declared_frames = round(int(stream_info["duration_ts"]) * numerator / denominator * rate)
        extra_tail = decoded[frames:]
        tail_rms = float(np.sqrt(np.mean(extra_tail.astype(np.float64) ** 2))) if len(extra_tail) else 0.0
        issues = []
        if (channels, width, rate, frames) != (item["channels"], 2, item["sampleRate"], item["frames"]):
            issues.append("format_or_frames")
        if digest(source) != item["sourceSha256"] or digest(runtime) != item["runtimeSha256"]:
            issues.append("stale_hash")
        if digest(source) in originals or digest(runtime) in originals:
            issues.append("source_byte_copy")
        # Vorbis granule duration is exact; the local FFmpeg decoder emits one
        # quiet tail packet for three 0.48-second clips. Check it explicitly,
        # rather than silently trimming samples or calling packet padding content.
        if declared_frames != frames or len(decoded) < frames - 256 or len(decoded) > frames + 2048 or tail_rms > .005:
            issues.append("codec_duration")
        for label, measured in [("wav", original), ("ogg", compressed)]:
            if measured["true_peak_4x"] >= .98 or measured["clipped_samples"]:
                issues.append(label + "_clipping")
            if measured["dc"] > .004 or measured["rms"] < .005:
                issues.append(label + "_dc_or_silence")
            if item["loop"] and measured["seam"] > max(.006, measured["adjacent_delta_p99"] * 1.75):
                issues.append(label + "_loop_seam")
            if not item["loop"] and measured["edge_peak"] > .025:
                issues.append(label + "_one_shot_edge")
        if item["category"] == "music":
            if min(original["rms_segments"]) < .012:
                issues.append("music_silent_padding")
            minimum = item["recipe"].get("reference_minimum_seconds")
            if minimum is not None and frames / rate < minimum:
                issues.append("music_reference_duration")
        checks.append(dict(id=item["id"], passed=not issues, issues=issues, source=original, runtime=compressed,
                           source_frames=frames, decoded_runtime_frames=len(decoded), seconds=frames / rate,
                           declared_runtime_frames=declared_frames, decoded_tail_padding_frames=max(0, len(decoded) - frames), decoded_tail_padding_rms=tail_rms,
                           semantic_listening_qa="PENDING", runtime_contextual_mix_qa="PENDING"))
        if args.preview:
            if item["category"] == "music":
                # An audible eight-second excerpt around the first developed verse.
                start = min(round(len(samples) * .20), max(0, len(samples) - RATE * 8))
                part = samples[start:start + RATE * 8].copy()
            else:
                part = samples[:RATE * 2].copy()
            if channels == 1:
                part = np.repeat(part, 2, axis=1)
            fade = min(RATE // 20, len(part) // 4)
            part[:fade] *= np.linspace(0, 1, fade)[:, None]
            part[-fade:] *= np.linspace(1, 0, fade)[:, None]
            preview.append((item["category"], item["id"], part))
        print(json.dumps({"id": item["id"], "passed": not issues, "issues": issues}), flush=True)
    sfx = [x for x in manifest["clips"] if x["category"] == "sfx"]
    full = [x for x in manifest["clips"] if x["category"] == "music" and x["recipe"]["kind"] == "full-composition"]
    shorts = [x for x in manifest["clips"] if x["category"] == "music" and x["recipe"]["kind"] == "short-score"]
    unique = len({item["sourceSha256"] for item in manifest["clips"]}) == len(manifest["clips"])
    counts_ok = (len(sfx), len(full), len(shorts)) == (72, 14, 11)
    motifs = [tuple(x["recipe"]["motif_semitones"]) for x in full + shorts]
    motifs_unique = len(set(motifs)) == 25
    source_match = digest(ROOT / manifest["generator"]) == manifest["generatorSha256"] and digest(ROOT / manifest["recipe"]) == manifest["recipeSha256"]
    report = dict(schema=1, passed=all(c["passed"] for c in checks) and unique and counts_ok and motifs_unique and source_match,
                  source_manifest_sha256=digest(manifest_path), sfx_count=len(sfx), full_composition_count=len(full), additional_score_count=len(shorts),
                  full_composition_seconds=sum(c["seconds"] for c in full), short_score_seconds=sum(c["seconds"] for c in shorts),
                  sfx_seconds=sum(c["seconds"] for c in sfx), distinct_source_hashes=unique, distinct_authored_motifs=motifs_unique,
                  authoring_source_matches=source_match, full_composition_minimum_seconds=3415.37415,
                  source_bytes=sum(x["sourceBytes"] for x in manifest["clips"]), runtime_bytes=sum(x["runtimeBytes"] for x in manifest["clips"]),
                  checks=checks, limits="Signal/codec/content-structure audit only. Not a subjective listening, musical equivalence, source event-branch, browser mix or human usability PASS.")
    if report["full_composition_seconds"] < 3415.37415:
        report["passed"] = False
    (REPORT / "audio-audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.preview:
        timeline = []
        for category in ["music", "sfx"]:
            parts = []; cursor = 0
            for group, identity, part in preview:
                if group != category:
                    continue
                timeline.append(dict(preview=category + "-preview.ogg", id=identity, start_seconds=cursor / RATE, duration_seconds=len(part) / RATE))
                parts += [part, np.zeros((RATE // 3, 2), dtype=np.float32)]
                cursor += len(part) + RATE // 3
            samples = np.concatenate(parts, axis=0)
            output = REPORT / (category + "-preview.ogg")
            process = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", "-", "-c:a", "libvorbis", "-q:a", "5", str(output)], input=samples.astype("<f4").tobytes(), capture_output=True)
            if process.returncode:
                raise RuntimeError("Preview encoding failed")
        (REPORT / "preview-timeline.json").write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
