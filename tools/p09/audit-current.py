"""Read-only staging audit with immutable, source-bound local receipts.

This does not deploy, restart, create accounts, run load, or modify VM files.
The fixed SSH identity is the existing authorized route, not an MCP bridge.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "https://racing-bois.158.180.59.36.sslip.io"
RELEASE = "p09-20260927-f"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compare_sources(expected, current):
    old = {row["path"]: row["sha256"] for row in expected["files"]}
    new = {row["path"]: row["sha256"] for row in current["files"]}
    changes = [{"path": path, "packagedSha256": old.get(path), "currentSha256": new.get(path)}
               for path in sorted(old.keys() | new.keys()) if old.get(path) != new.get(path)]
    return {"matches": not changes, "packagedSha256": expected["sha256"],
            "currentSha256": current["sha256"], "packagedFiles": len(old),
            "currentFiles": len(new), "changes": changes}


def local_sources():
    spec = importlib.util.spec_from_file_location("p09_package", ROOT / "tools/p09/package.py")
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    runtime = package.sources()
    indexed = {row["path"]: row["sha256"] for row in package.sources(include_tests=True)["files"]}
    for path in (ROOT / "Assets/RacingBois/Client/Application").glob("*.cs"):
        indexed[path.relative_to(ROOT).as_posix()] = digest(path)
    rows = [{"path": path, "sha256": sha} for path, sha in sorted(indexed.items())]
    tests = {"sha256": hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest(), "files": rows}
    return runtime, tests


def public_check(path):
    request = urllib.request.Request(ORIGIN + path, headers={"User-Agent": "RacingBois-ReadOnlyReadiness/1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
            body = json.load(response) if path == "/ready" else None
    except urllib.error.HTTPError as error:
        status, body = error.code, None
    result = {"path": path, "statusCode": status}
    if body is not None:
        # Only public readiness fields belong in this receipt.
        result["body"] = {key: body.get(key) for key in ("status", "protocolVersion", "contentHash")}
    return result


def remote_state():
    verifier = (ROOT / "tools/p09/infra/verify-deployment.py").read_text(encoding="utf8")
    # Capture the existing verifier's allowlisted report, then read existing
    # operational receipts. The backup key itself is only stat'ed by the verifier.
    script = "import contextlib,io,json,datetime,pathlib,hashlib\n"
    script += "capture=io.StringIO()\nwith contextlib.redirect_stdout(capture):\n    exec(" + repr(verifier) + ")\n"
    script += """
result=json.loads(capture.getvalue())
now=datetime.datetime.now(datetime.timezone.utc)
result['releaseManifestSha256']=hashlib.sha256((pathlib.Path('/srv/racing-bois/current')/'release.json').read_bytes()).hexdigest()
for field,path,time_key,allowed in [
 ('monitor','/var/lib/racing-bois-staging/monitor.json','generatedUtc',('generatedUtc','status','issues','diskFreeBytes','backupAgeSeconds','certificateDaysRemaining')),
 ('backup','/srv/racing-bois/backups/latest.json','createdUtc',('createdUtc','status','archiveSha256','archiveBytes'))]:
    raw=json.loads(pathlib.Path(path).read_text())
    safe={key:raw.get(key) for key in allowed}
    safe['ageSeconds']=(now-datetime.datetime.fromisoformat(raw[time_key])).total_seconds()
    result[field]=safe
print(json.dumps(result))
"""
    command = ["ssh", "-i", "C:/Users/Liquid/.ssh/jarvis_oci_ed25519", "-o", "BatchMode=yes",
               "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=15",
               "ubuntu@158.180.59.36", "sudo -n python3 -"]
    result = subprocess.run(command, input=script, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError("Read-only SSH verification failed; raw remote output suppressed")
    return json.loads(result.stdout)


def assess(manifest, package, local, remote, routes):
    failures = []
    if not local["source"]["matches"]:
        failures.append("deployed_runtime_source_differs_from_workspace")
    if not local["sourceStableDuringAudit"]:
        failures.append("runtime_source_changed_during_audit")
    if remote["releaseId"] != manifest["releaseId"] or remote["sourceSha256"] != manifest["source"]["sha256"]:
        failures.append("active_release_or_runtime_source_mismatch")
    if remote["releaseManifestSha256"] != package["manifestSha256"]:
        failures.append("active_manifest_mismatch")
    if remote["testSourceSha256"] != manifest["testSource"]["sha256"]:
        failures.append("active_packaged_test_source_mismatch")
    if remote["verifiedFiles"] != len(manifest["files"]):
        failures.append("active_file_count_mismatch")
    ready = next(row for row in routes if row["path"] == "/ready")
    if ready["statusCode"] != 200 or ready.get("body", {}).get("status") != "ready":
        failures.append("public_readiness_failed")
    if ready.get("body", {}).get("protocolVersion") != manifest["protocolVersion"]:
        failures.append("public_protocol_mismatch")
    if any(row["statusCode"] != 404 for row in routes if row["path"] != "/ready"):
        failures.append("private_route_is_public")
    health = remote["health"]["multiplayer"]
    if health["protocolVersion"] != manifest["protocolVersion"]:
        failures.append("private_multiplayer_protocol_mismatch")
    if health["persistenceFailures"] != 0:
        failures.append("persistence_failure_counter_nonzero")
    for name, limit in (("monitor", 600), ("backup", 7200)):
        report = remote[name]
        if report["status"] != "passed" or not 0 <= report["ageSeconds"] <= limit:
            failures.append(name + "_not_fresh_and_passed")
    if remote["monitor"]["issues"]:
        failures.append("monitor_reports_issues")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New JSON receipt; existing files are never replaced")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Receipt already exists; choose a new output path")
    started = dt.datetime.now(dt.timezone.utc)
    package = json.loads((ROOT / "docs/p09/releases/f/package.json").read_text(encoding="utf8"))
    manifest_path = ROOT / "Build/OciStaging" / RELEASE / "release.json"
    if digest(manifest_path) != package["manifestSha256"]:
        raise SystemExit("Local immutable release manifest differs from its package receipt")
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    before = local_sources()
    remote = remote_state()
    paths = ("/ready", "/health", "/health/", "/HEALTH", "/multiplayer/health", "/multiplayer/health/", "/metrics", "/ws", "/realm.sqlite3")
    routes = [public_check(path) for path in paths]
    after = local_sources()
    local = {"source": compare_sources(manifest["source"], after[0]),
             "testSource": compare_sources(manifest["testSource"], after[1]),
             "sourceStableDuringAudit": before[0] == after[0],
             "testSourceStableDuringAudit": before[1] == after[1]}
    failures = assess(manifest, package, local, remote, routes)
    warnings = []
    if not local["testSource"]["matches"]:
        warnings.append("Historical ARM tests cover packaged sources, not later workspace client/test changes")
    if not local["testSourceStableDuringAudit"]:
        warnings.append("Workspace test sources changed during this audit")
    report = {"schemaVersion": 1, "startedUtc": started.isoformat(),
              "completedUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "status": "passed_for_read_only_staging_scope" if not failures else "attention",
              "failures": failures, "warnings": warnings, "endpoint": ORIGIN,
              "auditSources": [{"path": path, "sha256": digest(ROOT / path)} for path in
                               ("tools/p09/audit-current.py", "tools/p09/package.py", "tools/p09/infra/verify-deployment.py")],
              "localSourceBinding": local, "deployment": remote, "publicRoutes": routes,
              "scope": "Read-only deployment bytes/process/privacy, source inventory, monitor/backup freshness and trusted HTTPS routes. No deployment, restart, load or account mutation.",
              "fullP09PhaseComplete": False,
              "exclusions": ["Rendered full Unity gameplay", "Regional game clients", "Capacity or performance",
                             "P08 visual/content acceptance", "Physical offline LAN", "Windows release acceptance"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "releaseId": remote["releaseId"],
                      "runtimeSourceMatches": local["source"]["matches"], "testSourceChanges": len(local["testSource"]["changes"]),
                      "failures": failures, "receipt": str(args.output)}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
