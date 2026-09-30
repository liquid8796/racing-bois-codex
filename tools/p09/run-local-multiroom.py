"""Measure simultaneous real socket rooms on a fresh, owned loopback backend."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("network_tools", ROOT / "tools/p10/run-network.py")
network = importlib.util.module_from_spec(spec)
spec.loader.exec_module(network)


def inventory():
    result = network.regression.source_inventory()
    for path in [Path(__file__), ROOT / "tools/p10/run-network.py", ROOT / "tools/p10/run-regression.py", *(ROOT / "tools/p10/ProtocolSoak").glob("*.cs"), *(ROOT / "tools/p10/ProtocolSoak").glob("*.csproj")]:
        result[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def health(origin):
    with urllib.request.urlopen(origin + "/multiplayer/health", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError("health_status")
        return json.load(response)


def histogram_delta(before, after):
    first, last = before["tickDurationHistogram"], after["tickDurationHistogram"]
    if first["bucketUpperBoundsMilliseconds"] != last["bucketUpperBoundsMilliseconds"]:
        raise RuntimeError("histogram_layout_changed")
    counts = [b - a for a, b in zip(first["bucketCounts"], last["bucketCounts"], strict=True)]
    if not counts or min(counts) < 0 or sum(counts) == 0:
        raise RuntimeError("histogram_counter_reset_or_empty")
    bounds = last["bucketUpperBoundsMilliseconds"]
    def percentile(fraction):
        cumulative = 0
        for bound, count in zip(bounds, counts, strict=True):
            cumulative += count
            if cumulative >= sum(counts) * fraction:
                return bound
    return {"tickSamples": sum(counts), "bucketCounts": counts, "bucketUpperBoundsMilliseconds": bounds,
            "p50UpperBoundMilliseconds": percentile(.5), "p95UpperBoundMilliseconds": percentile(.95), "p99UpperBoundMilliseconds": percentile(.99),
            "slowTicksDelta": after["slowTicks"] - before["slowTicks"],
            "droppedCatchupTicksDelta": after["droppedCatchupTicks"] - before["droppedCatchupTicks"],
            "persistenceFailuresDelta": after["persistenceFailures"] - before["persistenceFailures"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rooms", type=int, choices=range(2, 9), required=True)
    parser.add_argument("--seconds", type=int, default=180)
    args = parser.parse_args()
    if not 45 <= args.seconds <= 1800:
        parser.error("Use a bounded45..1800second run.")
    if sys.platform != "win32":
        parser.error("This supervisor records native Windows process counters.")
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "docs/p09/local-multiroom" / run_id
    private = ROOT / "_local/p09/local-multiroom" / run_id
    output.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    before = inventory()
    record = {"schema": 1, "runId": run_id, "status": "PREPARING", "startedUtc": network.regression.utc(),
              "rooms": args.rooms, "peersPerRoom": 8, "requestedSeconds": args.seconds, "sources": before,
              "sourceSha256": network.regression.digest(before), "hostPlatform": sys.platform,
              "scope": "Windows loopback backend and independent linked-production socket probes, one private eight-peer room per process. Shared authoring workstation; no isolated hardware benchmark, OCI capacity, geographic gameplay, rendered Unity or release acceptance.",
              "externalEndpointUsed": False, "phaseAccepted": False, "samples": [], "probes": []}
    receipt = output / "run.json"
    server = None
    children = []
    logs = []
    flags = subprocess.CREATE_NO_WINDOW
    network.write(receipt, record)
    try:
        for label, project in [("server", "src/Server/RacingBois.Server.Host"), ("probe", "tools/p10/ProtocolSoak")]:
            with (private / (label + "-publish.log")).open("wb") as log:
                result = subprocess.run(["dotnet", "publish", project, "-c", "Release", "--no-self-contained", "-o", str(private / label), "--nologo"],
                                        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180, creationflags=flags)
            if result.returncode:
                raise RuntimeError(label + "_publish_failed")
            record[label + "Files"] = network.tree(private / label)
        if before != inventory():
            raise RuntimeError("source_changed_during_publish")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        origin = "http://127.0.0.1:" + str(port)
        endpoint = "ws://127.0.0.1:" + str(port) + "/multiplayer"
        web = private / "empty-public"
        web.mkdir()
        log = (private / "server.log").open("wb"); logs.append(log)
        server = subprocess.Popen(["dotnet", str(private / "server/RacingBois.Server.Host.dll"), "--Port", str(port), "--AllowLan", "false", "--EnableTls", "false",
                                   "--RealmKind", "offline", "--DataRoot", str(private / "private-realm"), "--WebRoot", str(web), "--Logging:LogLevel:Default", "Warning"],
                                  cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
        record.update(serverPid=server.pid, endpoint=endpoint)
        deadline = time.monotonic() + 20
        while True:
            if server.poll() is not None:
                raise RuntimeError("owned_server_exited_before_ready")
            try:
                initial = health(origin)
                break
            except (OSError, ValueError):
                if time.monotonic() > deadline:
                    raise RuntimeError("owned_server_readiness_timeout")
                time.sleep(.2)
        record["before"] = initial
        for index in range(args.rooms):
            destination = output / ("room-" + str(index) + ".json")
            log = (private / ("room-" + str(index) + ".log")).open("wb"); logs.append(log)
            child = subprocess.Popen(["dotnet", str(private / "probe/ProtocolSoak.dll"), endpoint, str(destination), str(args.seconds), "8"],
                                     cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
            children.append(child)
            record["probes"].append({"index": index, "pid": child.pid, "report": destination.relative_to(ROOT).as_posix()})
        record["status"] = "RUNNING"
        network.write(receipt, record)
        print(json.dumps({"status": "RUNNING", "runId": run_id, "rooms": args.rooms, "peers": args.rooms * 8, "receipt": str(receipt)}), flush=True)
        began = time.monotonic()
        while any(child.poll() is None for child in children):
            if time.monotonic() - began > args.seconds + 90:
                raise RuntimeError("owned_probes_timeout")
            if server.poll() is not None:
                raise RuntimeError("owned_server_exited")
            current = health(origin)
            memory = network.process_memory(server)
            record["samples"].append({"utc": network.regression.utc(), "elapsedSeconds": time.monotonic() - began, "health": current, "serverMemory": memory})
            if memory is None or memory["privateBytes"] > 1024 * 1024 * 1024:
                raise RuntimeError("server_memory_unavailable_or_over_1GiB_safety_limit")
            if current["persistenceFailures"] != initial["persistenceFailures"]:
                raise RuntimeError("server_persistence_failure")
            if any(child.poll() not in (None, 0) for child in children):
                raise RuntimeError("room_probe_failed")
            network.write(receipt, record)
            time.sleep(2)
        record["after"] = health(origin)
        for child, item in zip(children, record["probes"], strict=True):
            path = ROOT / item["report"]
            payload = json.loads(path.read_text())
            item.update(exitCode=child.returncode, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), status=payload.get("status"),
                        sourceStable=payload.get("sourceStable"), elapsedSeconds=payload.get("elapsedSeconds"), cycles=payload.get("cycles"), reconnects=payload.get("reconnects"))
            if child.returncode != 0 or payload.get("status") != "PASS" or not payload.get("sourceStable") or len(payload.get("clients", [])) != 8:
                raise RuntimeError("room_result_failed")
        simultaneous = [s for s in record["samples"] if s["health"]["roomCount"] == args.rooms and s["health"]["sessionCount"] == args.rooms * 8]
        if len(simultaneous) < 2 or simultaneous[-1]["elapsedSeconds"] - simultaneous[0]["elapsedSeconds"] < args.seconds * .5:
            raise RuntimeError("insufficient_simultaneous_room_window")
        record["fullRoomWindow"] = {"firstUtc": simultaneous[0]["utc"], "lastUtc": simultaneous[-1]["utc"], "sampleCount": len(simultaneous),
                                    "elapsedSeconds": simultaneous[-1]["elapsedSeconds"] - simultaneous[0]["elapsedSeconds"],
                                    "scope": "Counters span first to last full-room observation; reconnects/result transitions inside that interval remain included.",
                                    **histogram_delta(simultaneous[0]["health"], simultaneous[-1]["health"])}
        record["wholeWindow"] = histogram_delta(initial, record["after"])
        after = inventory()
        record["changedSources"] = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
        record["sourceStable"] = not record["changedSources"]
        record["maximumObservedServerPrivateBytes"] = max(s["serverMemory"]["privateBytes"] for s in record["samples"])
        record["status"] = "PASS" if record["sourceStable"] else "SUPERSEDED"
    except Exception as error:
        record.update(status="FAIL", errorCode=str(error), errorType=type(error).__name__)
    finally:
        for label, process in [("probe-" + str(i), p) for i, p in enumerate(children)] + [("server", server)]:
            if process is None:
                continue
            stopped = process.poll() is None
            if stopped:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=10)
            record.setdefault("ownedProcessExit", []).append({"label": label, "pid": process.pid, "terminatedBySupervisor": stopped, "exitCode": process.returncode})
        for log in logs:
            log.close()
        record["completedUtc"] = network.regression.utc()
        network.write(receipt, record)
    print(json.dumps({key: record.get(key) for key in ("status", "runId", "errorCode", "fullRoomWindow", "maximumObservedServerPrivateBytes")}), flush=True)
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
