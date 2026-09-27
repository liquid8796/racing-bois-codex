"""Run real native suites with immutable per-run receipts and source drift checks."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SUITES = (
    ("Foundation", False), ("Gameplay", False), ("Prediction", False), ("PredictionProjection", False), ("PredictionImpulse", False), ("RetiredInput", False), ("RaceIntegration", False),
    ("Multiplayer.Integration", False), ("P05Client", False), ("P07Client", False),
    ("EconomyRules", False), ("Persistence", True), ("P08Content", True),
    ("DesktopConfig", True), ("NativeTransport", True), ("HostPolicy", False), ("MailboxConcurrency", False),
)


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def source_inventory():
    files = set()
    for base in ("src", "Packages/com.racingbois.foundation/Runtime", "Assets/RacingBois/Client/Application", "Assets/RacingBois/Client/Adapters", "tools/p09/HostPolicyTests", "tools/p10/MailboxRaceRepro"):
        for path in (ROOT / base).rglob("*"):
            if path.is_file() and path.suffix in {".cs", ".csproj", ".json", ".props", ".targets"} and not {"bin", "obj", "__pycache__"}.intersection(path.parts):
                files.add(path)
    files.add(ROOT / "global.json")
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}


def digest(inventory):
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", action="append", choices=[s[0] for s in SUITES])
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "docs/p10/regression" / run_id
    output.mkdir(parents=True, exist_ok=False)
    logs = ROOT / "_local/p10/regression" / run_id
    logs.mkdir(parents=True, exist_ok=False)
    before = source_inventory()
    receipt = {"schema": 1, "runId": run_id, "startedUtc": utc(), "status": "RUNNING", "sourceSha256": digest(before), "sources": before, "recipeSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "suites": [], "scope": "Native .NET linked production logic and real SQLite/loopback fixtures. Not a Unity player, visual, physical LAN, OCI, or final release acceptance receipt."}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    for name, flag in SUITES:
        if args.suite and name not in args.suite:
            continue
        report = output / (name + ".json")
        project = "tools/p09/HostPolicyTests" if name == "HostPolicy" else "tools/p10/MailboxRaceRepro" if name == "MailboxConcurrency" else "src/Tests/RacingBois." + name + ".Tests"
        command = ["dotnet", "run", "--project", project, "-c", "Release", "--"]
        command += (["--report"] if flag else []) + [str(report)]
        started = time.monotonic()
        print(f"RUN {name}", flush=True)
        timed_out = False
        with (logs / (name + ".log")).open("wb") as log:
            try:
                completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout, check=False)
                code = completed.returncode
            except subprocess.TimeoutExpired:
                code, timed_out = -1, True
        payload = json.loads(report.read_text(encoding="utf-8-sig")) if report.exists() else None
        count = 0
        if payload:
            count = payload.get("tests", payload.get("checks", []))
            count = len(count) if isinstance(count, list) else count
        failed = payload.get("failed", payload.get("failures", 0)) if payload else 1
        passed = code == 0 and payload is not None and count > 0 and not failed and payload.get("passed") is not False
        item = {"suite": name, "status": "PASS" if passed else "FAIL", "testGroups": count, "exitCode": code, "timedOut": timed_out, "elapsedSeconds": round(time.monotonic() - started, 3), "report": report.relative_to(ROOT).as_posix(), "reportSha256": hashlib.sha256(report.read_bytes()).hexdigest() if report.exists() else None}
        receipt["suites"].append(item)
        print(f"{item['status']} {name}: {count} groups, {item['elapsedSeconds']} s", flush=True)
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    after = source_inventory()
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    receipt.update(completedUtc=utc(), changedSources=changed, sourceStable=not changed, totalGroups=sum(s["testGroups"] for s in receipt["suites"]))
    receipt["status"] = "FAIL" if any(s["status"] != "PASS" for s in receipt["suites"]) else "SUPERSEDED" if changed else "PASS"
    receipt["pendingProductionGate"] = next((json.loads((ROOT / s["report"]).read_text(encoding="utf-8-sig")).get("pendingProductionGate") for s in receipt["suites"] if s["suite"] == "P08Content"), None)
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in ("runId", "status", "totalGroups", "sourceStable", "changedSources", "pendingProductionGate")}), flush=True)
    return 0 if receipt["status"] == "PASS" else 2 if receipt["status"] == "SUPERSEDED" else 1


if __name__ == "__main__":
    sys.exit(main())
