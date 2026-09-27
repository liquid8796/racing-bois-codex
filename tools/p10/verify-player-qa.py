"""Recompute native frame evidence and bind it to the actual audited player build."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("desktop_audit", ROOT / "tools/p08/desktop/audit_desktop.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def calculate(rows, initial_tick):
    """Deterministic derivation from every raw frame; unavailable samples stay absent."""
    durations = []
    totals = dict(raceCoverage=0.0, movingCoverage=0.0, focusCoverage=0.0, expectedDisplayCoverage=0.0, uiCoverage=0.0, advancingTickCoverage=0.0)
    previous_seconds = 0.0
    previous_frame = None
    last_tick, last_advance = initial_tick, 0.0
    cpu_frames = gpu_frames = gc_frames = 0
    max_working = max_private = max_unity = max_managed = max_driver = 0
    for row in rows:
        seconds, frame_ms = float(row["seconds"]), float(row["frame_ms"])
        require(math.isfinite(seconds) and math.isfinite(frame_ms) and frame_ms > 0 and seconds > previous_seconds, "Raw monotonic timing is invalid")
        delta = seconds - previous_seconds
        require(math.isclose(delta * 1000, frame_ms, rel_tol=1e-7, abs_tol=1e-4), "Raw elapsed time differs from frame intervals")
        frame = int(row["unity_frame"])
        require(previous_frame is None or frame == previous_frame + 1, "The raw sequence omits or repeats a Unity frame")
        for flag in ("online", "live_race", "content_ready", "content_loading", "input_blocked", "ui_present", "focused", "cinematic", "memory_sample", "screenshot_requested"):
            require(row[flag] in ("0", "1"), "Non-boolean raw state")
        live = row["live_race"] == "1"
        require(not live or row["content_ready"] == "1" and row["content_loading"] == "0" and row["cinematic"] == "0", "A claimed live race has unavailable content or a cinematic")
        speed = float(row["speed_m_s"])
        require(math.isfinite(speed), "Invalid speed sample")
        tick = int(row["tick"])
        if live:
            totals["raceCoverage"] += delta
            if speed > 1:
                totals["movingCoverage"] += delta
        if row["focused"] == "1": totals["focusCoverage"] += delta
        if row["ui_present"] == "1": totals["uiCoverage"] += delta
        if (int(row["width"]), int(row["height"]), int(row["quality"])) == (1920, 1080, 1): totals["expectedDisplayCoverage"] += delta
        if live and tick > last_tick: last_advance = seconds
        if live and seconds - last_advance <= .25: totals["advancingTickCoverage"] += delta
        for name in ("cpu_ms", "gpu_ms", "gc_bytes", "working_set_bytes", "private_bytes", "unity_allocated_bytes", "managed_bytes", "graphics_driver_bytes"):
            if row[name] != "":
                number = float(row[name]); require(math.isfinite(number) and number >= 0, "Invalid optional counter sample")
        cpu_frames += row["cpu_ms"] != ""
        gpu_frames += row["gpu_ms"] != ""
        gc_frames += row["gc_bytes"] != ""
        if row["memory_sample"] == "1":
            max_working = max(max_working, int(row["working_set_bytes"] or 0))
            max_private = max(max_private, int(row["private_bytes"] or 0))
            max_unity = max(max_unity, int(row["unity_allocated_bytes"] or 0))
            max_managed = max(max_managed, int(row["managed_bytes"] or 0))
            max_driver = max(max_driver, int(row["graphics_driver_bytes"] or 0))
        last_tick, previous_seconds, previous_frame = tick, seconds, frame
        durations.append(frame_ms)
        require(len(durations) <= 180000, "Raw frame capacity exceeded")
    require(durations and previous_seconds >= 600, "No complete 600-second measurement")
    durations.sort(); count = len(durations)
    result = dict(frames=count, measuredSeconds=previous_seconds, meanFps=count / previous_seconds,
        frameP50Ms=durations[math.ceil(count * .50) - 1], frameP95Ms=durations[math.ceil(count * .95) - 1],
        frameP99Ms=durations[math.ceil(count * .99) - 1], frameMaximumMs=durations[-1],
        cpuTimingFrames=cpu_frames, gpuTimingFrames=gpu_frames, gcFrames=gc_frames)
    result.update({key: value / previous_seconds for key, value in totals.items()})
    result["sampledMemoryMaxima"] = dict(workingSetBytes=max_working, privateBytes=max_private, unityAllocatedBytes=max_unity, managedBytes=max_managed, graphicsDriverBytes=max_driver)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", type=Path, required=True)
    args = parser.parse_args()
    directory = args.run_directory.resolve()
    launch = json.loads((directory / "launch.json").read_text(encoding="utf-8-sig"))
    config_path = directory / "config.json"
    require(digest(config_path) == launch["configSha256"], "Prepared QA config changed")
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    require(config["outputDirectory"] == str(directory / "runtime"), "QA runtime root differs from prepared run")
    build_path = Path(config["buildReceiptPath"])
    require(digest(build_path) == config["buildReceiptSha256"], "Actual build receipt changed")
    build = json.loads(build_path.read_text(encoding="utf-8-sig"))
    installation = audit.audit_player(Path(launch["playerRoot"]), build_path, build["contentHash"])
    receipt_path = directory / "runtime/receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    require(receipt.get("schema") == 1 and receipt.get("runId") == config["runId"], "Runtime receipt is from another run")
    for field in ("buildReceiptSha256", "sourceFingerprint", "executableSha256", "bootstrapSha256", "manifestSha256"):
        require(receipt.get(field) == config[field], "Runtime identity mismatch: " + field)
    require(receipt.get("contentHash") == installation["contentHash"], "Gameplay content identity differs")
    raw = receipt["rawFrames"]
    require(raw["path"] == "raw-frames.csv", "Raw frame path is invalid")
    raw_path = directory / "runtime/raw-frames.csv"
    require(raw_path.stat().st_size == raw["bytes"] and raw_path.stat().st_size <= 128 * 1024 * 1024 and digest(raw_path) == raw["sha256"], "Raw frame bytes differ")
    with raw_path.open(newline="", encoding="utf-8") as stream:
        derived = calculate(csv.DictReader(stream), receipt["initialTick"])
    for key, value in derived.items():
        if key != "sampledMemoryMaxima":
            require(key in receipt and math.isclose(receipt[key], value, rel_tol=1e-7, abs_tol=1e-6), "Reported summary differs from raw frames: " + key)
    require(receipt.get("identityStable") is True and receipt.get("status") == "PASS" and receipt.get("passed") is True, "Native recorder did not pass")
    require(receipt["warnings"] == 0 and receipt["errors"] == 0, "Player emitted diagnostics during recording")
    require(derived["meanFps"] >= 60 and derived["frameP95Ms"] <= 20 and derived["raceCoverage"] >= .95 and derived["movingCoverage"] >= .80,
        "Observed timing or actual moving-race coverage did not meet the declared budget")
    require(all(derived[name] >= threshold for name, threshold in (("focusCoverage", .99), ("expectedDisplayCoverage", .99), ("uiCoverage", .99), ("advancingTickCoverage", .95))), "Native presentation coverage is insufficient")
    require(0 < receipt["maxWorkingSetBytes"] <= 2 * 1024**3 and 0 < derived["sampledMemoryMaxima"]["workingSetBytes"] <= receipt["maxWorkingSetBytes"], "Observed process memory failed its budget")
    for file in receipt["screenshots"]:
        require(file["path"] in ("frame-01.png", "frame-02.png", "frame-03.png"), "Unexpected capture path")
        path = directory / "runtime" / file["path"]
        require(path.stat().st_size == file["bytes"] and digest(path) == file["sha256"], "Actual screenshot bytes changed")
    result = {"status": "PASS", "runId": config["runId"], "runtimeReceiptSha256": digest(receipt_path), "rawFramesSha256": digest(raw_path),
        "sourceFingerprint": installation["sourceFingerprint"], "derived": derived,
        "scope": "Raw native frame and build/file binding verification. Does not prove visual fidelity, physical-device input, human usability, physical LAN, global regions or release completeness."}
    destination = directory / "verification.json"
    require(not destination.exists(), "Preserve the previous verification receipt")
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
