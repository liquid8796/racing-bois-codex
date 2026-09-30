"""Verify the paced multiroom run from its raw probes and source/binary bindings."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def delta(first, last):
    before, after = first["tickDurationHistogram"], last["tickDurationHistogram"]
    bounds = before["bucketUpperBoundsMilliseconds"]
    require(bounds == after["bucketUpperBoundsMilliseconds"], "histogram layout changed")
    require(len(bounds) == len(before["bucketCounts"]) == len(after["bucketCounts"]), "histogram lengths")
    counts = [b - a for a, b in zip(before["bucketCounts"], after["bucketCounts"])]
    require(counts and min(counts) >= 0 and sum(counts) > 0, "counter reset or empty histogram")
    def percentile(fraction):
        count = 0
        for upper, value in zip(bounds, counts):
            count += value
            if count >= sum(counts) * fraction:
                return upper
    return {"tickSamples": sum(counts), "bucketCounts": counts, "bucketUpperBoundsMilliseconds": bounds,
            "p50UpperBoundMilliseconds": percentile(.5), "p95UpperBoundMilliseconds": percentile(.95), "p99UpperBoundMilliseconds": percentile(.99),
            **{name + "Delta": last[name] - first[name] for name in ("slowTicks", "droppedCatchupTicks", "persistenceFailures")}}


def verify_summary(run, probes):
    require(run["schema"] == 1 and run["status"] == "PASS" and run["sourceStable"] and not run["changedSources"], "passing stable run required")
    require(not run["externalEndpointUsed"] and not run["phaseAccepted"], "scope changed")
    rooms = run["rooms"]
    require(2 <= rooms <= 8 and run["peersPerRoom"] == 8, "room/player bounds")
    require(run["launchIntervalSeconds"] == 25 and run["rampSeconds"] == (rooms - 1) * 25, "ramp policy changed")
    require(len(run["probes"]) == len(probes) == rooms and len({p["runId"] for p in probes}) == rooms, "distinct probe count")
    require(len(run["ownedProcessExit"]) == rooms + 1, "owned child cleanup incomplete")
    for index, (bound, probe) in enumerate(zip(run["probes"], probes)):
        require(bound["index"] == index and bound["exitCode"] == 0 and bound["status"] == "PASS" and bound["sourceStable"], "bound probe failed")
        require(probe["status"] == "PASS" and probe["sourceStable"] and not probe["changedSources"], "probe failed or stale")
        require(probe["endpoint"] == run["endpoint"] and probe["peers"] == 8 and len(probe["clients"]) == 8, "probe endpoint/player mismatch")
        require(probe["requestedSeconds"] == bound["requestedSeconds"] and probe["elapsedSeconds"] >= probe["requestedSeconds"], "truncated run")
        require(index * 25 <= bound["launchOffsetSeconds"] < index * 25 + 5 and probe["requestedSeconds"] >= run["requestedSeconds"] - 5, "launch window differs")
        require(probe["reconnects"] > 0 and probe["errorCode"] is None, "missing resume or error")
        require(all(p["ProgressSamples"] > 0 and p["MaximumDistance"] > 10 and p["InvalidSnapshots"] == 0 and p["MaximumPending"] <= 120 for p in probe["clients"]), "client race/queue invariant")
        require(all(run["sources"].get(path) == value for path, value in probe["sources"].items()), "probe not bound to supervisor inputs")
        closed = run["ownedProcessExit"][index]
        require(closed["pid"] == bound["pid"] and closed["label"] == "probe-" + str(index) and closed["exitCode"] == 0 and not closed["terminatedBySupervisor"], "probe did not finish normally")
    server = run["ownedProcessExit"][-1]
    require(server["label"] == "server" and server["pid"] == run["serverPid"] and server["terminatedBySupervisor"] and server["exitCode"] is not None, "owned backend not stopped")
    samples = run["samples"]
    require(all(a["elapsedSeconds"] < b["elapsedSeconds"] for a, b in zip(samples, samples[1:])), "sample clock not increasing")
    require(len({s["health"]["realmId"] for s in samples}) == 1 and all(s["health"]["realmKind"] == "offline" for s in samples), "realm identity changed")
    require(all(s["health"]["persistenceFailures"] == run["before"]["persistenceFailures"] for s in samples), "persistence failure")
    require(max(s["serverMemory"]["privateBytes"] for s in samples) == run["maximumObservedServerPrivateBytes"] <= 1024**3, "memory binding/bound differs")
    full = [s for s in samples if s["health"]["roomCount"] == rooms and s["health"]["sessionCount"] == rooms * 8]
    require(len(full) >= 2 and full[-1]["elapsedSeconds"] - full[0]["elapsedSeconds"] >= run["requestedSeconds"] * .5, "missing simultaneous room window")
    window = run["fullRoomWindow"]
    require(window["firstUtc"] == full[0]["utc"] and window["lastUtc"] == full[-1]["utc"] and window["sampleCount"] == len(full), "window sample binding")
    require(window["elapsedSeconds"] == full[-1]["elapsedSeconds"] - full[0]["elapsedSeconds"], "window duration differs")
    measured = delta(full[0]["health"], full[-1]["health"])
    require(all(window[key] == value for key, value in measured.items()), "window summary differs from raw counters")
    require(run["wholeWindow"] == delta(run["before"], run["after"]), "whole summary differs from raw counters")
    return {"rooms": rooms, "clients": rooms * 8, "windowSeconds": window["elapsedSeconds"], "tickSamples": measured["tickSamples"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run_path, output = args.run.resolve(), args.output.resolve()
    require(run_path.is_relative_to(ROOT / "docs/p09/local-multiroom-ramp") and output.parent == run_path.parent and not output.exists(), "fresh same-run output required")
    run = json.loads(run_path.read_text())
    probes = []
    for bound in run["probes"]:
        path = (ROOT / bound["report"]).resolve()
        require(path.parent == run_path.parent and sha(path) == bound["sha256"], "probe receipt hash/path")
        probes.append(json.loads(path.read_text()))
    summary = verify_summary(run, probes)
    expected = hashlib.sha256(json.dumps(run["sources"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(run["sourceSha256"] == expected, "source fingerprint differs")
    for name, digest in run["sources"].items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT) and path.is_file() and sha(path) == digest, "current source differs: " + name)
    private = ROOT / "_local/p09/local-multiroom-ramp" / run["runId"]
    for kind in ("server", "probe"):
        directory = private / kind
        actual = {p.relative_to(directory).as_posix(): sha(p) for p in directory.rglob("*") if p.is_file()}
        require(actual == run[kind + "Files"], "published " + kind + " bytes differ")
    report = {"schema": 1, "passed": True, "run": run_path.relative_to(ROOT).as_posix(), "runSha256": sha(run_path),
              "verifierSha256": sha(Path(__file__)), "rawProbesVerified": len(probes), "sourceFilesVerified": len(run["sources"]),
              "binaryFilesVerified": sum(len(run[k + "Files"]) for k in ("server", "probe")), **summary,
              "scope": "Raw loopback multiroom evidence and exact current source/binary verification only; no OCI/player/fidelity/phase acceptance."}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
