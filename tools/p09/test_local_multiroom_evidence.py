"""Tamper controls against the separately implemented raw-evidence verifier."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "tools/p09/verify-local-multiroom.py"
spec = importlib.util.spec_from_file_location("verifier", path)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
run_path = ROOT / "docs/p09/local-multiroom/20260928T021243Z/run.json"
original = json.loads(run_path.read_text())
original_probes = [json.loads((ROOT / row["report"]).read_text()) for row in original["probes"]]
checks = []
verifier.verify_summary(original, original_probes)
checks.append({"name": "actual_two_room_run", "passed": True})

for case in ("failed_child", "duplicate_room", "missing_child", "truncated_duration", "no_resume", "invalid_snapshot", "no_progress", "stale_probe", "source_substitution", "incomplete_cleanup", "unsampled_room_count", "forged_histogram", "reset_histogram", "false_memory", "realm_switch", "phase_acceptance"):
    run, probes = copy.deepcopy(original), copy.deepcopy(original_probes)
    if case == "failed_child": probes[0]["status"] = "FAIL"
    if case == "duplicate_room": probes[1]["runId"] = probes[0]["runId"]
    if case == "missing_child": probes.pop()
    if case == "truncated_duration": probes[0]["elapsedSeconds"] = 1
    if case == "no_resume": probes[0]["reconnects"] = 0
    if case == "invalid_snapshot": probes[0]["clients"][0]["InvalidSnapshots"] = 1
    if case == "no_progress": probes[0]["clients"][0]["ProgressSamples"] = 0
    if case == "stale_probe": probes[0]["sourceStable"] = False
    if case == "source_substitution": probes[0]["sources"][next(iter(probes[0]["sources"]))] = "0" * 64
    if case == "incomplete_cleanup": run["ownedProcessExit"].pop()
    if case == "unsampled_room_count":
        for sample in run["samples"]: sample["health"]["roomCount"] = 1
    if case == "forged_histogram": run["fullRoomWindow"]["tickSamples"] += 1
    if case == "reset_histogram": run["after"]["tickDurationHistogram"]["bucketCounts"] = [0] * len(run["after"]["tickDurationHistogram"]["bucketCounts"])
    if case == "false_memory": run["maximumObservedServerPrivateBytes"] = 1
    if case == "realm_switch": run["samples"][-1]["health"]["realmId"] = "different-realm"
    if case == "phase_acceptance": run["phaseAccepted"] = True
    try:
        verifier.verify_summary(run, probes)
    except (ValueError, KeyError, IndexError):
        checks.append({"name": case, "passed": True})
    else:
        raise AssertionError("tampered evidence accepted: " + case)
output = ROOT / "docs/p09/local-multiroom/verifier-controls-20260928.json"
assert not output.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = {"schema": 1, "passed": True, "checks": checks, "testSha256": sha(Path(__file__)), "verifierSha256": sha(path), "runSha256": sha(run_path),
          "scope": "16 negative mutations of real raw-loopback evidence plus unchanged positive control; no new runtime/OCI/release acceptance."}
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"passed": True, "checks": len(checks)}))
