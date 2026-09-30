"""Resume a persisted Tripo task through GET only; never resubmit generation."""
import argparse
import json
from pathlib import Path
import re
import time

from api import api_call, ApiFailure
from keyring import Keyring, fetch_balance
from generate_candidate import ROOT, exclusive_job, recorded_cost, relative, transport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--key-file", type=Path, default=Path("C:/Users/Liquid/Desktop/tripo_api_key.txt"))
    args = parser.parse_args()
    with exclusive_job():
        directory = args.candidate.resolve(strict=True)
        if not directory.is_relative_to(ROOT / "ArtSource/P08/Tripo"):
            raise transport.SafeFailure("Recovery requires an owned Tripo candidate directory.")
        path = directory / "receipt.json"
        receipt = json.loads(path.read_text())
        task_id = receipt.get("taskId")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", task_id):
            raise transport.SafeFailure("No persisted task ID; inspect the rejected/unknown submission separately.")
        ring = Keyring(args.key_file)
        key = next((key for key in ring.keys() if key.fingerprint == receipt.get("keyFingerprint")), None)
        if key is None:
            raise transport.SafeFailure("The task's key is unavailable; no new task was submitted.")
        save = lambda: transport.write_json(path, receipt)
        receipt["recoveryStartedUtc"] = transport.utc_now()
        receipt["recoveryUsesGenerationPost"] = False
        save()
        deadline = time.monotonic() + 1800
        failures = 0
        while time.monotonic() < deadline:
            ring.inventory()  # Discover appended keys without changing the task's authenticated owner.
            try:
                data = api_call(key.authentication_value(), "GET", "/tasks/" + task_id)
                failures = 0
            except ApiFailure:
                failures += 1
                if failures > 6:
                    raise
                time.sleep(10)
                continue
            status = data.get("status")
            receipt["taskStatus"] = status
            if data.get("credits_consumed") is not None:
                receipt["creditsConsumed"] = float(recorded_cost(data["credits_consumed"]))
            if status in {"failed", "cancelled", "banned"}:
                receipt["pipelineStatus"] = "task_terminal_failure"
                save()
                raise transport.SafeFailure("The persisted task ended without a model.")
            if status == "success":
                outputs = data.get("output") or {}
                for name, url, destination, limit, preview in [
                    ("model", outputs.get("model_url"), directory / "model.glb", 600 * 1024**2, False),
                    ("preview", outputs.get("rendered_image_url"), directory / "preview", 32 * 1024**2, True),
                ]:
                    if name == "preview" and not url:
                        continue
                    existing = receipt.setdefault("artifacts", {}).get(name)
                    if existing:
                        saved = Path(existing["path"]).resolve()
                        allowed = {"model.glb"} if name == "model" else {"preview.png", "preview.jpg", "preview.webp"}
                        if saved.parent != directory or saved.name not in allowed:
                            raise transport.SafeFailure("Receipt artifact must belong to this candidate and expected filename.")
                    if existing and Path(existing["path"]).is_file() and transport.sha256_file(Path(existing["path"])) == existing["sha256"]:
                        continue
                    for old in ([destination] if not preview else [directory / ("preview" + extension) for extension in (".png", ".jpg", ".webp")]):
                        if old.exists():
                            preserved = old.with_name(old.stem + "-incomplete-" + str(time.time_ns()) + old.suffix)
                            relative(old); relative(preserved)
                            old.rename(preserved)
                            receipt.setdefault("preservedIncompleteDownloads", []).append(relative(preserved))
                    receipt["pipelineStatus"] = "downloading"
                    save()
                    receipt["artifacts"][name] = transport.download_asset(url, destination, limit, preview=preview)
                    save()
                proof = fetch_balance(key)
                receipt["walletAfter"] = proof.summary()
                receipt.update(pipelineStatus="completed", recoveredUtc=transport.utc_now())
                receipt.pop("failure", None)
                if proof.balance == 0 and proof.frozen == 0:
                    receipt["exhaustedKeyRemoval"] = ring.remove_confirmed_empty(key, proof).summary()
                receipt["keyInventory"] = ring.inventory().summary()
                save()
                print(json.dumps({"pipelineStatus": "completed", "taskId": task_id, "creditsConsumed": receipt.get("creditsConsumed")}))
                return 0
            if status not in {"queued", "running"}:
                raise transport.SafeFailure("Unknown task status; preserve the existing receipt.")
            save()
            time.sleep(5)
        raise transport.SafeFailure("Recovery wait expired; the task ID is still persisted.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("Recovery stopped; preserved task and artifacts can be inspected without another generation POST.")
        raise SystemExit(1)
