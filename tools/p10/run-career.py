"""Real HTTPS/WSS account and economy verification on two private native realms."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
from importlib.util import spec_from_file_location, module_from_spec

ROOT = Path(__file__).resolve().parents[2]
spec = spec_from_file_location("network", Path(__file__).with_name("run-network.py"))
network = module_from_spec(spec)
spec.loader.exec_module(network)


def main():
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output, private = ROOT / "docs/p10/career" / run_id, ROOT / "_local/p10/career" / run_id
    output.mkdir(parents=True, exist_ok=False); private.mkdir(parents=True, exist_ok=False)
    before = network.regression.source_inventory()
    record = {"schema": 1, "runId": run_id, "status": "PREPARING", "startedUtc": network.regression.utc(), "sources": before, "sourceSha256": network.regression.digest(before), "tlsValidation": "Standard OS trust, existing localhost certificate; no trust changes or bypass."}
    receipt = output / "run.json"
    network.write(receipt, record)
    processes, streams, endpoints = [], [], []
    try:
        for label, project in (("server", "src/Server/RacingBois.Server.Host"), ("probe", "src/Tests/RacingBois.Career.LiveProbe")):
            with (private / (label + "-build.log")).open("wb") as log:
                completed = subprocess.run(["dotnet", "publish", project, "-c", "Release", "--no-self-contained", "-o", str(private / label), "--nologo"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            if completed.returncode: raise RuntimeError(label + "_publish_failed")
            record[label + "Files"] = network.tree(private / label)
        after = network.regression.source_inventory()
        if before != after: raise RuntimeError("source_changed_during_publish")
        # Bind all reservations at once to obtain four distinct ports without touching existing listeners.
        reservations = [socket.socket() for _ in range(4)]
        for reservation in reservations: reservation.bind(("127.0.0.1", 0))
        ports = [reservation.getsockname()[1] for reservation in reservations]
        for reservation in reservations: reservation.close()
        for index, realm in enumerate(("offline", "online")):
            port, tls_port = ports[index * 2:index * 2 + 2]
            web = private / (realm + "-empty-public"); web.mkdir()
            log = (private / (realm + ".log")).open("wb"); streams.append(log)
            command = ["dotnet", str(private / "server/RacingBois.Server.Host.dll"), "--Port", str(port), "--TlsPort", str(tls_port), "--EnableTls", "true", "--AllowLan", "false", "--RealmKind", realm, "--DataRoot", str(private / (realm + "-private")), "--WebRoot", str(web), "--Logging:LogLevel:Default", "Warning"]
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            processes.append(process)
            record[realm + "Pid"] = process.pid
            for _ in range(100):
                if process.poll() is not None: raise RuntimeError(realm + "_host_start_failed")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=1) as ready:
                        if ready.status == 200: break
                except Exception: time.sleep(.1)
            else: raise RuntimeError(realm + "_readiness_timeout")
            endpoints.extend([f"https://localhost:{tls_port}/", f"http://127.0.0.1:{port}/"])
        record.update(status="RUNNING", endpoints=endpoints)
        network.write(receipt, record)
        print("RUN isolated HTTPS/WSS account and economy probe", flush=True)
        report = output / "probe.json"
        command = ["dotnet", str(private / "probe/RacingBois.Career.LiveProbe.dll"), *endpoints[:2], str(report), *endpoints[2:]]
        with (private / "probe.log").open("wb") as log:
            probe = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        data = json.loads(report.read_text()) if report.exists() else {}
        record["probeExitCode"] = probe.returncode
        record["checks"] = data.get("tests", 0)
        if probe.returncode or not data.get("passed") or not data.get("tests") or data.get("skippedTests"):
            raise RuntimeError("career_probe_failed_or_skipped")
        after = network.regression.source_inventory()
        changes = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
        record.update(status="SUPERSEDED" if changes else "PASS", sourceStable=not changes, changedSources=changes, probeSha256=hashlib.sha256(report.read_bytes()).hexdigest())
    except Exception as error:
        record.update(status="FAIL", errorCode=str(error))
    finally:
        for process in processes:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=10)
        for stream in streams: stream.close()
        record["completedUtc"] = network.regression.utc()
        network.write(receipt, record)
    print(json.dumps({key: record.get(key) for key in ("runId", "status", "checks", "errorCode", "changedSources")}), flush=True)
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
