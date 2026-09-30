"""Direct Tripo generation with live key inventory and immutable candidate receipts."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
import os
import sys
import time

from keyring import Keyring, fetch_balance
from api import ApiFailure, api_call

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("trial_transport", ROOT / "tools/tripo_api_trial/generate.py")
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)

PROFILES = {
    "high-quality-parts": ({"model": "v3.1-20260211", "texture": False, "pbr": False,
                            "geometry_quality": "detailed", "generate_parts": True}, 60, 100),
    "high-quality": ({"model": "v3.1-20260211", "texture": True, "pbr": True,
                      "texture_version": "v3.5-20260815", "texture_quality": "extreme", "delight": True,
                      "geometry_quality": "detailed", "generate_parts": False}, 80, 120),
    "low-poly": ({"model": "P1-20260311", "texture": True, "pbr": True, "face_limit": 20000}, 50, 80),
    "ui-extraction": ({"model": "seedream_v5", "size": "2K", "output_format": "png", "watermark": False}, 10, 30),
}


def relative(path):
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise transport.SafeFailure("Candidate inputs/outputs must remain within the repository.")
    return resolved.relative_to(ROOT).as_posix()


@contextmanager
def exclusive_job():
    """One generation client per checkout; no concurrent cap checks or reservations."""
    path = ROOT / "_local/p08/tripo/generation.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0"); stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise transport.SafeFailure("Another generation client owns the checkout reservation.") from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def recorded_cost(value):
    try:
        result = Decimal(str(value))
    except Exception:
        raise transport.SafeFailure("An existing receipt has invalid credit accounting.") from None
    if isinstance(value, bool) or not result.is_finite() or result < 0:
        raise transport.SafeFailure("An existing receipt has invalid credit accounting.")
    return result


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, default=Path("C:/Users/Liquid/Desktop/tripo_api_key.txt"))
    parser.add_argument("--profile", choices=PROFILES, default="high-quality-parts")
    parser.add_argument("--prompt-file", type=Path, help="Reviewed UI image-editing instruction; required for ui-extraction")
    args = parser.parse_args()
    keyring = Keyring(args.key_file)
    candidate = args.out.resolve()
    if candidate.exists() and any(candidate.iterdir()):
        raise transport.SafeFailure("Use a fresh output; inspect any persisted task before resubmitting.")
    relative(candidate)
    for path in (args.input, args.reference):
        relative(path)
        if not path.is_file():
            raise transport.SafeFailure("Required input/reference missing.")
    if args.input.suffix.lower() not in {".png", ".jpg", ".jpeg"} or args.input.stat().st_size > transport.MAX_IMAGE_BYTES:
        raise transport.SafeFailure("A reviewed PNG/JPEG under20MiB is required.")
    parameters, expected_cost, budget = PROFILES[args.profile]
    parameters = dict(parameters)
    image_job = args.profile == "ui-extraction"
    prompt_file = None
    if image_job:
        if args.prompt_file is None:
            raise transport.SafeFailure("A reviewed prompt file is required for UI image extraction.")
        relative(args.prompt_file)
        prompt = args.prompt_file.read_text(encoding="utf-8").strip()
        if not prompt or len(prompt) > 1024:
            raise transport.SafeFailure("UI prompt must contain1..1024 characters.")
        parameters["prompt"] = prompt
        prompt_file = {"path": relative(args.prompt_file), "sha256": transport.sha256_file(args.prompt_file), "characters": len(prompt)}
    elif args.prompt_file is not None:
        raise transport.SafeFailure("Prompt file is only supported by the UI image profile.")
    route = "/generation/image-to-image" if image_job else "/generation/image-to-model"
    if parameters["model"].startswith("v3"):
        parameters.update(enable_image_autofix=False)
        if not parameters.get("generate_parts"):
            parameters.update(quad=False, smart_low_poly=False)
    candidate.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "racing-bois.tripo-candidate.v2", "createdUtc": transport.utc_now(),
               "status": "unaccepted", "visualAccepted": False, "productionAccepted": False,
               "freeCreditsAuthorizedByUser": True, "maximumCreditsPerKey": 600,
               "profile": args.profile, "expectedCreditsEstimate": expected_cost, "preflightBudget": budget,
               "jobKind": "image_to_image" if image_job else "image_to_model", "route": route,
               "promptFile": prompt_file,
               "budgetScope": "Balance and per-key task receipts are checked locally; the API exposes no documented task hard spending cap.",
               "input": {"path": relative(args.input), "sha256": transport.sha256_file(args.input)},
               "reference": {"path": relative(args.reference), "sha256": transport.sha256_file(args.reference)},
               "requestParameters": parameters, "keyAttempts": [], "pipelineStatus": "preflight", "taskId": None, "artifacts": {}}
    receipt_path = candidate / "receipt.json"
    save = lambda: transport.write_json(receipt_path, receipt)
    save()
    key = None
    previous_inventory = None
    try:
        excluded = set()
        while True:
            inventory = keyring.inventory().summary()
            receipt["keyInventory"] = inventory
            save()
            key = keyring.select(exclude_fingerprints=frozenset(excluded))
            if key is None:
                raise transport.SafeFailure("No currently usable key; keep positive/unknown keys and refresh after the list changes.")
            excluded.add(key.fingerprint)
            try:
                proof = fetch_balance(key, version="v3")
            except Exception:
                receipt["keyAttempts"].append({"fingerprint": key.fingerprint, "balanceUnavailable": True})
                save()
                continue
            receipt["keyAttempts"].append({"fingerprint": key.fingerprint, "wallet": proof.summary()})
            save()
            if proof.balance == 0 and proof.frozen == 0:
                keyring.remove_confirmed_empty(key, proof)
                continue
            if proof.frozen != 0 or proof.balance < Decimal(budget):
                continue
            prior_spend = Decimal(0)
            for path in (ROOT / "ArtSource/P08/Tripo").rglob("receipt.json"):
                old = json.loads(path.read_text(encoding="utf-8"))
                if old.get("keyFingerprint") == key.fingerprint:
                    prior_spend += recorded_cost(old.get("creditsConsumed", 0))
                    if old.get("pipelineStatus") in {"submission_pending", "submission_unknown_do_not_retry", "task_submitted", "downloading"}:
                        raise transport.SafeFailure("This key has a persisted unsettled task; recover it before another submission.")
            prior_spend = max(prior_spend, Decimal(600) - proof.balance - proof.frozen)
            if prior_spend + Decimal(budget) > 600:
                continue
            receipt.update(keyFingerprint=key.fingerprint, walletBefore=proof.summary(), previousRecordedCredits=float(prior_spend))
            token = transport.upload_image(key.authentication_value(), args.input)
            receipt["pipelineStatus"] = "submission_pending"
            save()
            try:
                task = api_call(key.authentication_value(), "POST", route, {"input": token, **parameters})
            except ApiFailure as error:
                # Only a definitive rejection can select another key. Unknown POST outcomes stop.
                if error.definitive_rejection:
                    receipt["keyAttempts"][-1]["submissionRejection"] = error.summary()
                    receipt["pipelineStatus"] = "submission_rejected"
                    save()
                    # Diagnose parameter/account/task-slot rejection; it is not evidence of exhausted credit.
                    raise
                receipt["pipelineStatus"] = "submission_unknown_do_not_retry"
                save()
                raise
            task_id = task.get("task_id")
            if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", task_id):
                receipt["pipelineStatus"] = "submission_unknown_do_not_retry"
                save()
                raise transport.SafeFailure("Submission lacks a valid task ID; no retry is permitted.")
            receipt.update(taskId=task_id, pipelineStatus="task_submitted")
            transport.write_json(candidate / "task.json", {"task_id": task_id, "keyFingerprint": key.fingerprint}, exclusive=True)
            save()
            print(json.dumps({"taskId": task_id, "profile": args.profile, "inventory": inventory}), flush=True)
            break
        deadline = time.monotonic() + 1800
        previous = None
        transient_failures = 0
        while time.monotonic() < deadline:
            inventory = keyring.inventory().summary()
            if inventory != previous_inventory:
                receipt["keyInventory"] = inventory
                print(json.dumps({"keyInventoryRefreshed": inventory}), flush=True)
                previous_inventory = inventory
            try:
                data = api_call(key.authentication_value(), "GET", "/tasks/" + receipt["taskId"])
                transient_failures = 0
            except ApiFailure:
                transient_failures += 1
                if transient_failures > 6:
                    raise transport.SafeFailure("Task polling unavailable; recover the saved task ID before continuing.") from None
                time.sleep(10)
                continue
            status = data.get("status")
            if status not in {"queued", "running", "success", "failed", "cancelled", "banned"}:
                raise transport.SafeFailure("Unknown task state; recover the persisted task ID.")
            progress = data.get("progress")
            progress = progress if isinstance(progress, int) and not isinstance(progress, bool) and 0 <= progress <= 100 else None
            receipt.update(taskStatus=status, progress=progress)
            cost = data.get("credits_consumed")
            if cost is not None:
                receipt["creditsConsumed"] = float(recorded_cost(cost))
            save()
            if (status, progress) != previous:
                print(json.dumps({"taskStatus": status, "progress": progress}), flush=True)
                previous = (status, progress)
            if status in {"failed", "cancelled", "banned"}:
                receipt["pipelineStatus"] = "task_terminal_failure"
                save()
                raise transport.SafeFailure("Task failed; its receipt and credit observation are retained.")
            if status == "success":
                output = data.get("output") or {}
                receipt["pipelineStatus"] = "downloading"
                save()
                if image_job:
                    receipt["artifacts"]["image"] = transport.download_asset(output.get("generated_image_url"), candidate / "image", 32 * 1024 * 1024, preview=True)
                else:
                    receipt["artifacts"]["model"] = transport.download_asset(output.get("model_url"), candidate / "model.glb", 600 * 1024 * 1024)
                save()
                if not image_job and output.get("rendered_image_url"):
                    receipt["artifacts"]["preview"] = transport.download_asset(output["rendered_image_url"], candidate / "preview", 32 * 1024 * 1024, preview=True)
                receipt.update(pipelineStatus="completed", completedUtc=transport.utc_now())
                save()
                break
            time.sleep(5)
        else:
            raise transport.SafeFailure("Polling timed out; recover the saved task ID before resubmission.")
        after = fetch_balance(key, version="v3")
        receipt["walletAfter"] = after.summary()
        if after.balance == 0 and after.frozen == 0:
            receipt["exhaustedKeyRemoval"] = keyring.remove_confirmed_empty(key, after).summary()
        receipt["keyInventory"] = keyring.inventory().summary()
        save()
        print(json.dumps({"pipelineStatus": receipt["pipelineStatus"], "creditsConsumed": receipt.get("creditsConsumed"), "walletAfter": after.summary()}), flush=True)
        return 0
    except Exception as error:
        receipt["failure"] = str(error) if isinstance(error, (transport.SafeFailure, ApiFailure)) else "Local operation failed; preserve the task receipt before continuing."
        save()
        print(json.dumps({"pipelineStatus": receipt["pipelineStatus"], "failure": receipt["failure"], "taskId": receipt["taskId"]}), flush=True)
        return 1


def main():
    with exclusive_job():
        return run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("Candidate preflight failed; no raw error or credential was logged.", file=sys.stderr)
        raise SystemExit(1)
