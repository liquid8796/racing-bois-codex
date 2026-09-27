"""Prepare a bound native QA config after auditing an actual immutable player build."""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("desktop_audit", ROOT / "tools/p08/desktop/audit_desktop.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player-root", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, default=ROOT / "docs/p08/desktop/build.json")
    parser.add_argument("--screenshots", action="store_true")
    args = parser.parse_args()
    player = args.player_root.resolve()
    build_path = args.build_receipt.resolve()
    build = json.loads(build_path.read_text(encoding="utf-8-sig"))
    distribution = audit.audit_player(player, build_path, build["contentHash"])
    run_id = uuid.uuid4().hex
    directory = ROOT / "docs/p10/player" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    build_bytes = build_path.read_bytes()
    if hashlib.sha256(build_bytes).hexdigest() != distribution["unityBuildReceiptSha256"]:
        raise ValueError("Build receipt changed during QA preparation")
    build_path = directory / "build-receipt.json"
    build_path.write_bytes(build_bytes)
    build = json.loads(build_bytes.decode("utf-8-sig"))
    files = {row["path"]: row for row in distribution["entries"]}
    config = {"schema": 1, "runId": run_id, "outputDirectory": str(directory / "runtime"), "buildReceiptPath": str(build_path),
        "buildReceiptSha256": hashlib.sha256(build_bytes).hexdigest(), "sourceFingerprint": build["sourceFingerprint"],
        "executableSha256": files["RacingBois.exe"]["sha256"], "bootstrapSha256": files["RacingBois_Data/Managed/RacingBois.Client.Bootstrap.dll"]["sha256"],
        "manifestSha256": build["manifestSha256"], "durationSeconds": 600, "warmupSeconds": 10, "raceWaitTimeoutSeconds": 300, "captureScreenshots": args.screenshots}
    config_path = directory / "config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    (directory / "distribution-audit.json").write_text(json.dumps(distribution, indent=2), encoding="utf-8")
    launch = {"generatedUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "state": "PREPARED_NOT_RUN", "executable": str(player / "RacingBois.exe"),
        "arguments": ["--rb-qa-config", str(config_path), "-logFile", str(directory / "player.log")], "playerRoot": str(player),
        "configSha256": hashlib.sha256(config_path.read_bytes()).hexdigest(), "recipeSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Actual audited installation and config preparation only. No player launch or input/performance acceptance inferred."}
    (directory / "launch.json").write_text(json.dumps(launch, indent=2), encoding="utf-8")
    print(json.dumps(launch, indent=2))


if __name__ == "__main__": main()
