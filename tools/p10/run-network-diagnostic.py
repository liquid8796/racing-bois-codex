"""Own an isolated native backend/probe run; never reuse or stop existing servers."""
from __future__ import annotations
import argparse
import ctypes
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
spec = spec_from_file_location("regression", Path(__file__).with_name("run-regression.py"))
regression = module_from_spec(spec)
spec.loader.exec_module(regression)


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def tree(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob("*")) if p.is_file()}


def process_memory(process):
    if sys.platform != "win32":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in
            ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]
    data = Counters(); data.cb = ctypes.sizeof(data)
    read = ctypes.windll.psapi.GetProcessMemoryInfo
    read.argtypes = (ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong)
    read.restype = ctypes.c_int
    if not read(int(process._handle), ctypes.byref(data), ctypes.sizeof(data)):
        return None
    return {"workingSetBytes": data.WorkingSetSize, "privateBytes": data.PrivateUsage, "peakWorkingSetBytes": data.PeakWorkingSetSize}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--peers", type=int, default=8)
    parser.add_argument("--fuzz", action="store_true")
    parser.add_argument("--endpoint", help="Optional explicitly selected real WSS server. Default: a new isolated local backend.")
    parser.add_argument("--health-url", help="Same-origin /ready for deployments that keep detailed metrics private.")
    args = parser.parse_args()
    if not 30 <= args.seconds <= 86400 or not 1 <= args.peers <= 8:
        parser.error("Duration 30..86400 seconds and peers 1..8 are required.")
    if args.endpoint and not args.endpoint.startswith("wss://"):
        parser.error("External probes require WSS with normal certificate validation.")
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "docs/p10/network" / run_id
    output.mkdir(parents=True, exist_ok=False)
    private = ROOT / "_local/p10/network" / run_id
    private.mkdir(parents=True, exist_ok=False)
    before = regression.source_inventory()
    for path in (ROOT / "tools/p10/ProtocolSoakNext").glob("*"):
        if path.is_file() and path.suffix in {".cs", ".csproj"}:
            before[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    linked_diagnostics = ("tools/p10/correction-audit/CorrectionTrace.cs", "tools/p10/correction-audit/MultiplayerSession.CorrectionAudit.cs")
    for path in linked_diagnostics:
        before[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    harness_paths = {path: sha for path, sha in before.items() if path.startswith("tools/p10/ProtocolSoakNext/") or path in linked_diagnostics}
    def inventory():
        current = regression.source_inventory()
        current.update({path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() if (ROOT / path).exists() else None for path in harness_paths})
        return current
    record = {"schema": 1, "runId": run_id, "status": "PREPARING", "startedUtc": regression.utc(), "sources": before, "sourceSha256": regression.digest(before), "recipeSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "seconds": args.seconds, "peers": args.peers, "fixturePrivateRoot": str(private), "tlsValidation": "standard OS validation; no bypass"}
    receipt = output / "run.json"
    write(receipt, record)
    server = None
    files = []
    server_log = None
    probe_log = None
    try:
        for label, project in [("probe", "tools/p10/ProtocolSoakNext"), *(([("server", "src/Server/RacingBois.Server.Host")]) if not args.endpoint else [])]:
            destination = private / label
            with (private / (label + "-build.log")).open("wb") as build_log:
                built = subprocess.run(["dotnet", "publish", project, "-c", "Release", "--no-self-contained", "-o", str(destination), "--nologo"], cwd=ROOT, stdout=build_log, stderr=subprocess.STDOUT, timeout=180)
            if built.returncode:
                raise RuntimeError(label + "_publish_failed")
            record[label + "Files"] = tree(destination)
        after_build = inventory()
        changed = [p for p in before.keys() | after_build.keys() if before.get(p) != after_build.get(p)]
        if changed:
            record["changedDuringBuild"] = sorted(changed)
            raise RuntimeError("source_changed_during_publish")
        endpoint = args.endpoint
        if not endpoint:
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            web = private / "empty-public"
            web.mkdir()
            server_log = (private / "server.log").open("wb")
            server = subprocess.Popen(["dotnet", str(private / "server/RacingBois.Server.Host.dll"), "--Port", str(port), "--AllowLan", "false", "--EnableTls", "false", "--RealmKind", "offline", "--DataRoot", str(private / "private-realm"), "--WebRoot", str(web), "--Logging:LogLevel:Default", "Warning"], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            record["serverPid"] = server.pid
            record["serverCommandScope"] = "This run's copied DLL with loopback-only listener, independent private realm and empty public directory."
            endpoint = f"ws://127.0.0.1:{port}/multiplayer"
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("owned_server_exited_before_ready")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=1) as ready:
                        if ready.status == 200:
                            break
                except Exception:
                    time.sleep(.1)
            else:
                raise RuntimeError("owned_server_readiness_timeout")
        record.update(status="RUNNING", endpoint=endpoint, runStartedUtc=regression.utc())
        write(receipt, record)
        command = ["dotnet", str(private / "probe/ProtocolSoakNext.dll"), endpoint, str(output / "probe.json"), str(args.seconds), str(args.peers)] + (["--fuzz"] if args.fuzz else []) + (["--health-url", args.health_url] if args.health_url else [])
        probe_log = (private / "probe.log").open("wb")
        probe = subprocess.Popen(command, cwd=ROOT, stdout=probe_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        record["probePid"] = probe.pid
        write(receipt, record)
        print(json.dumps({"runId": run_id, "status": "RUNNING", "endpoint": endpoint, "serverPid": record.get("serverPid"), "probePid": probe.pid, "receipt": str(receipt)}), flush=True)
        began = time.monotonic()
        next_sample = began
        while probe.poll() is None:
            if time.monotonic() - began > args.seconds + 120:
                probe.kill(); probe.wait(timeout=10)
                raise RuntimeError("owned_probe_timeout")
            if time.monotonic() >= next_sample:
                for label, process in (("server", server), ("probe", probe)):
                    sample = process_memory(process) if process else None
                    if sample:
                        memory = record.setdefault(label + "Memory", {"samples": 0, "first": sample, "maximumPrivateBytes": 0, "maximumWorkingSetBytes": 0})
                        memory.update(samples=memory["samples"] + 1, latest=sample, maximumPrivateBytes=max(memory["maximumPrivateBytes"], sample["privateBytes"]), maximumWorkingSetBytes=max(memory["maximumWorkingSetBytes"], sample["workingSetBytes"]))
                        if time.monotonic() - began >= 60 and "afterWarmup" not in memory:
                            memory["afterWarmup"] = sample
                write(receipt, record)
                next_sample = time.monotonic() + 30
            time.sleep(1)
        code = probe.returncode
        record["probeExitCode"] = code
        result_path = output / "probe.json"
        result = json.loads(result_path.read_text()) if result_path.exists() else {}
        if code != 0 or result.get("status") != "PASS":
            raise RuntimeError("probe_failed_" + str(result.get("errorCode", "missing_receipt")))
        after = inventory()
        changes = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
        record.update(status="SUPERSEDED" if changes else "PASS", changedSources=changes, sourceStable=not changes, probeSha256=hashlib.sha256(result_path.read_bytes()).hexdigest())
    except Exception as error:
        record.update(status="FAIL", errorCode=str(error))
    finally:
        if server is not None:
            # Only this process handle is owned; no name/PID scan or old session metadata is used.
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait(timeout=10)
            record["ownedServerExitCode"] = server.returncode
        if server_log: server_log.close()
        if probe_log: probe_log.close()
        record["completedUtc"] = regression.utc()
        write(receipt, record)
    print(json.dumps({k: record.get(k) for k in ("runId", "status", "errorCode", "changedSources")}), flush=True)
    return 0 if record["status"] == "PASS" else 2 if record["status"] == "SUPERSEDED" else 1


if __name__ == "__main__":
    sys.exit(main())

