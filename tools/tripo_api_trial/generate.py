#!/usr/bin/env python3
"""Create one unaccepted Tripo candidate using confirmed free trial credits.

The API key is read once from standard input. It is never written to disk,
placed in a receipt, or included in an error message. Generation submissions
are never retried, including when a timeout leaves their outcome unknown.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
import uuid


BASE_URL = "https://openapi.tripo3d.ai/v3"
MODEL = "v3.1-20260211"
CONSERVATIVE_BUDGET = 50
MAX_IMAGE_BYTES = 20 * 1024 * 1024
POLL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 600


class SafeFailure(Exception):
    """An error whose message is safe to display and persist."""


class NoApiRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A redirect must never forward the account's bearer key elsewhere.
        raise SafeFailure("Tripo API returned an unexpected redirect.")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict, *, exclusive: bool = False) -> None:
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def api_call(key: str, method: str, route: str, body=None, content_type=None) -> dict:
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    if isinstance(body, dict):
        body = json.dumps(body, allow_nan=False).encode("utf-8")
        content_type = "application/json"
    if content_type:
        headers["Content-Type"] = content_type
    request = Request(BASE_URL + route, data=body, method=method, headers=headers)
    try:
        # Do not add retries: a failed POST can have been accepted server-side.
        with build_opener(NoApiRedirect()).open(request, timeout=120) as response:
            raw = response.read(1024 * 1024 + 1)
    except HTTPError as error:
        raise SafeFailure(f"Tripo API request failed (HTTP {error.code}).") from None
    except (URLError, TimeoutError, OSError):
        raise SafeFailure("Tripo API request failed or timed out; no POST was retried.") from None
    if len(raw) > 1024 * 1024:
        raise SafeFailure("Tripo API returned an oversized response.")
    try:
        response_json = json.loads(raw)
    except (ValueError, UnicodeError):
        raise SafeFailure("Tripo API returned invalid JSON.") from None
    if not isinstance(response_json, dict):
        raise SafeFailure("Tripo API returned an unexpected response shape.")
    if response_json.get("code") != 0:
        code = response_json.get("code")
        suffix = f" (code {code})" if isinstance(code, int) else ""
        # Do not expose vendor error text, which can contain request metadata.
        raise SafeFailure("Tripo API rejected the request" + suffix + ".")
    data = response_json.get("data")
    if not isinstance(data, dict):
        raise SafeFailure("Tripo API returned an unexpected data shape.")
    return data


def wallet(key: str) -> dict:
    data = api_call(key, "GET", "/account/balance")
    result = {}
    for field in ("balance", "frozen"):
        value = data.get(field)
        if isinstance(value, bool):
            raise SafeFailure("Tripo balance response contains an invalid amount.")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise SafeFailure("Tripo balance response contains an invalid amount.") from None
        if not math.isfinite(number) or number < 0:
            raise SafeFailure("Tripo balance response contains an invalid amount.")
        result[field] = number
    return result


def upload_image(key: str, path: Path) -> str:
    image_bytes = path.read_bytes()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise SafeFailure("Input image exceeds Tripo's 20 MB limit.")
    boundary = "tripo-trial-" + uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    suffix = ".png" if path.suffix.lower() == ".png" else ".jpg"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="input{suffix}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("ascii")
    body = prefix + image_bytes + f"\r\n--{boundary}--\r\n".encode("ascii")
    data = api_call(key, "POST", "/files", body, "multipart/form-data; boundary=" + boundary)
    token = data.get("file_token")
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", token):
        raise SafeFailure("Tripo upload returned an invalid file token.")
    return token


def download_asset(url, path: Path, byte_limit: int, *, preview: bool = False) -> dict:
    if not isinstance(url, str):
        raise SafeFailure("The completed task did not provide an artifact URL.")
    try:
        parts = urlsplit(url)
        valid = parts.scheme == "https" and bool(parts.hostname) and not parts.username and not parts.password
    except ValueError:
        valid = False
    if not valid:
        raise SafeFailure("Tripo returned an invalid HTTPS artifact URL.")
    try:
        # Signed CDN URLs authenticate themselves. NEVER attach the API key.
        with urlopen(Request(url, headers={"User-Agent": "RacingBois-TripoTrial/1"}), timeout=120) as response:
            first = response.read(1024 * 1024)
            if preview:
                if first.startswith(b"\x89PNG\r\n\x1a\n"):
                    path = path.with_suffix(".png")
                elif first.startswith(b"\xff\xd8\xff"):
                    path = path.with_suffix(".jpg")
                elif first.startswith(b"RIFF") and first[8:12] == b"WEBP":
                    path = path.with_suffix(".webp")
                else:
                    raise SafeFailure("Downloaded preview is not a supported PNG, JPEG, or WebP image.")
            elif not first.startswith(b"glTF"):
                raise SafeFailure("Downloaded model is not a binary GLB file.")
            total = 0
            with path.open("xb") as stream:
                chunk = first
                while chunk:
                    total += len(chunk)
                    if total > byte_limit:
                        raise SafeFailure("Downloaded artifact exceeds the configured size limit.")
                    stream.write(chunk)
                    chunk = response.read(1024 * 1024)
                stream.flush()
                os.fsync(stream.fileno())
    except SafeFailure:
        raise
    except (HTTPError, URLError, TimeoutError, OSError):
        raise SafeFailure("Artifact download failed; its signed URL was not logged.") from None
    if total == 0:
        raise SafeFailure("Downloaded artifact is empty.")
    return {"path": str(path), "bytes": total, "sha256": sha256_file(path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Reviewed single-asset PNG/JPEG input")
    parser.add_argument("--reference", type=Path, required=True, help="Exact approved concept version to hash")
    parser.add_argument("--out", type=Path, required=True, help="New or empty candidate output directory")
    parser.add_argument("--trial-confirmed", action="store_true", required=True,
                        help="Human confirmed the available credits are free trial credits")
    parser.add_argument("--texture", action="store_true",
                        help="Use standard texture and PBR (published 30 credits; geometry-only 20)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    key = ""
    receipt = None
    receipt_path = None
    task_submitted = False
    try:
        input_path = args.input.resolve(strict=True)
        reference_path = args.reference.resolve(strict=True)
        if not input_path.is_file() or input_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise SafeFailure("Input must be a PNG or JPEG file.")
        if not reference_path.is_file():
            raise SafeFailure("Reference must be a file.")
        if input_path.stat().st_size > MAX_IMAGE_BYTES:
            raise SafeFailure("Input image exceeds Tripo's 20 MB limit.")
        output_path = args.out.resolve()
        if output_path.exists() and (not output_path.is_dir() or any(output_path.iterdir())):
            raise SafeFailure("Output must be a new or empty directory; an existing task cannot be overwritten.")
        output_path.mkdir(parents=True, exist_ok=True)
        request_parameters = {
            "model": MODEL,
            "texture": bool(args.texture),
            "pbr": bool(args.texture),
            "texture_quality": "standard",
            "geometry_quality": "standard",
            "enable_image_autofix": False,
            "quad": False,
            "smart_low_poly": False,
            "generate_parts": False,
        }
        receipt_path = output_path / "receipt.json"
        receipt = {
            "schema": "racing-bois.tripo-api-trial.v1",
            "created_at": utc_now(),
            "status": "unaccepted",
            "accepted": False,
            "acceptance_reason": "Candidate requires rendered comparison with the approved concept.",
            "pipeline_status": "preflight",
            "free_trial_confirmed_by_user": True,
            "billing_limitation": "Balance API is aggregate; trial provenance is user-confirmed, not API-verified.",
            "published_expected_credits": 30 if args.texture else 20,
            "conservative_credit_budget": CONSERVATIVE_BUDGET,
            "budget_enforcement": "Preflight balance check only; API exposes no documented hard spending cap.",
            "input": {"path": str(input_path), "sha256": sha256_file(input_path)},
            "reference": {"path": str(reference_path), "sha256": sha256_file(reference_path)},
            "request_parameters": request_parameters,
            "task_id": None,
            "artifacts": {},
        }
        write_json(receipt_path, receipt, exclusive=True)
        if sys.stdin.isatty():
            raise SafeFailure("Provide the key through standard input using a secret-safe caller; interactive echo is disabled.")
        key = sys.stdin.readline().strip()
        if not re.fullmatch(r"tsk_[A-Za-z0-9_-]{12,512}", key):
            key = ""
            raise SafeFailure("Standard input did not contain a valid Tripo API key.")
        before = wallet(key)
        receipt["wallet_before"] = before
        write_json(receipt_path, receipt)
        if before["frozen"] != 0:
            raise SafeFailure("Existing frozen credits prevent an isolated one-task trial.")
        if before["balance"] < CONSERVATIVE_BUDGET:
            raise SafeFailure("Available trial balance is below the conservative 50-credit preflight budget.")
        print(f"Preflight passed: balance={before['balance']:g}, frozen=0; submitting one candidate.", flush=True)
        file_token = upload_image(key, input_path)
        receipt["pipeline_status"] = "input_uploaded"
        write_json(receipt_path, receipt)
        # Persist the submission boundary before issuing the single mutation.
        # Any unknown outcome must be inspected rather than automatically retried.
        receipt["pipeline_status"] = "submission_pending"
        write_json(receipt_path, receipt)
        task = api_call(key, "POST", "/generation/image-to-model", {"input": file_token, **request_parameters})
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", task_id):
            raise SafeFailure("Tripo task submission returned an invalid task identifier; do not resubmit.")
        task_submitted = True
        receipt["task_id"] = task_id
        # Save the identifier before polling, downloading, or other API calls.
        write_json(output_path / "task.json", {"task_id": task_id, "created_at": utc_now()}, exclusive=True)
        receipt["pipeline_status"] = "task_submitted"
        write_json(receipt_path, receipt)
        print(f"Task persisted: {task_id}", flush=True)
        deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
        previous_progress = None
        while time.monotonic() < deadline:
            data = api_call(key, "GET", "/tasks/" + task_id)
            status = data.get("status")
            if status not in {"queued", "running", "success", "failed", "cancelled", "banned"}:
                raise SafeFailure("Tripo returned an unknown task status; the task identifier is saved.")
            progress = data.get("progress")
            progress = progress if isinstance(progress, int) and 0 <= progress <= 100 else None
            current_progress = (status, progress)
            if current_progress != previous_progress:
                print(f"Task {status}" + (f": {progress}%" if progress is not None else ""), flush=True)
                previous_progress = current_progress
            receipt["task_status"] = status
            receipt["progress"] = progress
            cost = data.get("credits_consumed")
            if isinstance(cost, (int, float)) and not isinstance(cost, bool) and math.isfinite(cost) and cost >= 0:
                receipt["credits_consumed"] = cost
            if isinstance(data.get("error_code"), int):
                receipt["task_error_code"] = data["error_code"]
            write_json(receipt_path, receipt)
            if status in {"failed", "cancelled", "banned"}:
                raise SafeFailure(f"Tripo task ended with status {status}; no generation retry was made.")
            if status == "success":
                outputs = data.get("output")
                if not isinstance(outputs, dict):
                    raise SafeFailure("Successful task lacks output metadata.")
                model_url = outputs.get("model_url")
                preview_url = outputs.get("rendered_image_url")
                receipt["pipeline_status"] = "downloading"
                write_json(receipt_path, receipt)
                receipt["artifacts"]["model"] = download_asset(model_url, output_path / "model.glb", 300 * 1024 * 1024)
                write_json(receipt_path, receipt)
                receipt["artifacts"]["preview"] = download_asset(preview_url, output_path / "preview", 32 * 1024 * 1024, preview=True)
                receipt["pipeline_status"] = "completed"
                receipt["completed_at"] = utc_now()
                write_json(receipt_path, receipt)
                print("Candidate and preview saved. Acceptance remains unaccepted pending rendered review.", flush=True)
                return 0
            time.sleep(POLL_SECONDS)
        raise SafeFailure("Polling reached 10 minutes; the saved task may still run. Do not submit another task.")
    except SafeFailure as error:
        message = str(error)
        print("Stopped: " + message, file=sys.stderr, flush=True)
        if receipt is not None:
            receipt["failure"] = message
            if receipt.get("pipeline_status") == "submission_pending" and not task_submitted:
                receipt["pipeline_status"] = "submission_unknown_do_not_retry"
            else:
                receipt["pipeline_status"] = "stopped"
        return 1
    except Exception:
        # Raw exception text/tracebacks can leak URLs, keys, or vendor payloads.
        message = "Local operation failed; inspect the sanitized receipt and saved task before continuing."
        print("Stopped: " + message, file=sys.stderr, flush=True)
        if receipt is not None:
            receipt["failure"] = message
            receipt["pipeline_status"] = "submission_unknown_do_not_retry" if receipt.get("pipeline_status") == "submission_pending" else "stopped"
        return 1
    finally:
        if receipt is not None and receipt_path is not None:
            if key:
                try:
                    after = wallet(key)
                    receipt["wallet_after"] = after
                    before = receipt.get("wallet_before")
                    if before:
                        receipt["balance_delta"] = before["balance"] - after["balance"]
                    print(f"Final wallet: balance={after['balance']:g}, frozen={after['frozen']:g}", flush=True)
                except Exception:
                    receipt["wallet_after_unavailable"] = True
            receipt["updated_at"] = utc_now()
            try:
                write_json(receipt_path, receipt)
            except Exception:
                print("Final receipt update failed; preserve the output directory and saved task.", file=sys.stderr, flush=True)
        key = ""


if __name__ == "__main__":
    raise SystemExit(main())
