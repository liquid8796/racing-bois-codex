"""Offline UI-image dispatch, provenance, recovery and credit-cap controls."""
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


# Import guards are scoped so discovery alongside the other test modules cannot
# leave out-of-order global patch stacks. Every test gets its own active guards.
with patch("socket.socket.connect", side_effect=AssertionError("Offline UI test blocked networking.")), \
     patch("socket.socket.connect_ex", side_effect=AssertionError("Offline UI test blocked networking.")):
    import generate_candidate as candidate
    import recover_candidate as recovery
    import keyring


class _Ring:
    def __init__(self, keys):
        self.members = list(keys)
        self.refreshes = 0
        self.removed = []

    def keys(self):
        self.refreshes += 1
        return tuple(self.members)

    def inventory(self):
        self.refreshes += 1
        return keyring.Inventory(len(self.members), len(self.members), 0, 0, 0,
                                 tuple(key.fingerprint for key in self.members))

    def select(self, *, exclude_fingerprints=frozenset(), **kwargs):
        self.refreshes += 1
        return next((key for key in self.members if key.fingerprint not in exclude_fingerprints), None)

    def remove_confirmed_empty(self, key, proof):
        proof.require_empty(key)
        self.removed.append(key.fingerprint)
        self.members = [existing for existing in self.members if existing.fingerprint != key.fingerprint]
        return keyring.RemovalResult(key.fingerprint, 1, self.inventory())


class UiCandidateTests(unittest.TestCase):
    def setUp(self):
        self.network_guards = []
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "urllib.request.OpenerDirector.open"):
            guard = patch(name, side_effect=AssertionError("Offline UI test blocked networking."))
            self.network_guards.append(guard.start())
            self.addCleanup(guard.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / "reviewed-input.png"
        self.reference = self.root / "locked-reference.png"
        self.prompt_file = self.root / "reviewed-prompt.txt"
        self.input.write_bytes(b"\x89PNG\r\n\x1a\ndummy-source")
        self.reference.write_bytes(b"\x89PNG\r\n\x1a\ndummy-concept")
        self.prompt_file.write_bytes(b"  Extract the reviewed cabinet image with the specified layout.\r\n")
        self.output = self.root / "ArtSource/P08/Tripo/UI/Dummy/candidate01"
        self.secret = "tsk_dummy_ui_alpha_credential"
        self.other_secret = "tsk_dummy_ui_beta_credential"
        self.key = keyring.KeyRef(self.secret)
        self.other_key = keyring.KeyRef(self.other_secret)
        self.ring = _Ring([self.key])
        self.balance = Decimal(600)
        self.frozen = Decimal(0)
        self.balance_calls = []
        self.api_calls = []
        self.upload_calls = []
        self.download_calls = []
        self.task_result = {"status": "success", "progress": 100, "credits_consumed": 10,
                            "output": {"generated_image_url": "https://example.invalid/ui.png"}}
        self.post_failure = None
        self.download_failure = None
        self.stdout, self.stderr = StringIO(), StringIO()
        self.png = b"\x89PNG\r\n\x1a\ndummy-delivered-image"

    def assert_offline(self):
        for guard in self.network_guards:
            guard.assert_not_called()

    def wallet(self, key, *, version="v3"):
        self.balance_calls.append(key.fingerprint)
        return keyring.VerifiedBalance.from_response(key, http_status=200,
            body={"code": 0, "data": {"balance": str(self.balance), "frozen": str(self.frozen)}},
            endpoint=keyring.BALANCE_ENDPOINTS[version])

    def api(self, key, method, route, body=None):
        self.api_calls.append((key, method, route, body))
        if method == "POST":
            if self.post_failure:
                raise self.post_failure
            return {"task_id": "task_dummy_ui_01"}
        return self.task_result

    def upload(self, key, path):
        self.upload_calls.append((key, path))
        return "file_dummy_ui"

    def download(self, url, path, limit, *, preview=False):
        self.download_calls.append((url, path, limit, preview))
        if self.download_failure:
            raise self.download_failure
        if not isinstance(url, str):
            raise candidate.transport.SafeFailure("Expected image delivery URL is missing.")
        if not preview or path.name != "image":
            raise candidate.transport.SafeFailure("UI job attempted a model or preview delivery.")
        path = path.with_suffix(".png")
        path.write_bytes(self.png)
        return {"path": str(path), "bytes": len(self.png), "sha256": candidate.transport.sha256_file(path)}

    def run_client(self, *, prompt=True, profile="ui-extraction"):
        args = ["generate_candidate.py", "--input", str(self.input), "--reference", str(self.reference),
                "--out", str(self.output), "--profile", profile, "--key-file", str(self.root / "dummy-keys-never-read.txt")]
        if prompt:
            args.extend(("--prompt-file", str(self.prompt_file)))
        with patch.object(candidate, "ROOT", self.root), patch.object(candidate, "Keyring", return_value=self.ring), \
             patch.object(candidate, "fetch_balance", side_effect=self.wallet), \
             patch.object(candidate, "api_call", side_effect=self.api), \
             patch.object(candidate.transport, "upload_image", side_effect=self.upload), \
             patch.object(candidate.transport, "download_asset", side_effect=self.download), \
             patch.object(candidate.time, "sleep"), patch.object(sys, "argv", args), \
             redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            try:
                return candidate.run()
            finally:
                self.assert_offline()

    def receipt(self):
        return json.loads((self.output / "receipt.json").read_text(encoding="utf-8"))

    def posts(self):
        return [call for call in self.api_calls if call[1] == "POST"]

    def assert_no_secret_output(self):
        text = self.stdout.getvalue() + self.stderr.getvalue()
        if self.output.exists():
            for path in self.output.rglob("*.json"):
                text += path.read_text(encoding="utf-8")
        self.assertNotIn(self.secret, text)
        self.assertNotIn(self.other_secret, text)

    def prior(self, cost):
        path = self.root / "ArtSource/P08/Tripo/prior/receipt.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"keyFingerprint": self.key.fingerprint,
                                    "pipelineStatus": "completed", "creditsConsumed": cost}), encoding="utf-8")

    def persisted(self, **updates):
        self.output.mkdir(parents=True)
        value = {"schema": "racing-bois.tripo-candidate.v2", "profile": "ui-extraction", "jobKind": "image_to_image",
                 "taskId": "task_dummy_ui_01", "keyFingerprint": self.key.fingerprint,
                 "pipelineStatus": "task_submitted", "status": "unaccepted", "visualAccepted": False,
                 "productionAccepted": False, "artifacts": {}, **updates}
        (self.output / "receipt.json").write_text(json.dumps(value), encoding="utf-8")

    def run_recovery(self):
        args = ["recover_candidate.py", str(self.output), "--key-file", str(self.root / "dummy-keys-never-read.txt")]
        with patch.object(candidate, "ROOT", self.root), patch.object(recovery, "ROOT", self.root), \
             patch.object(recovery, "Keyring", return_value=self.ring), \
             patch.object(recovery, "fetch_balance", side_effect=self.wallet), \
             patch.object(recovery, "api_call", side_effect=self.api), \
             patch.object(recovery.transport, "download_asset", side_effect=self.download), \
             patch.object(recovery.time, "sleep"), patch.object(sys, "argv", args), \
             redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            try:
                return recovery.main()
            finally:
                self.assert_offline()
                self.assertFalse(self.posts(), "Recovery must never submit generation.")

    def test_only_reviewed_ui_route_and_exact_body_are_submitted(self):
        self.assertEqual(self.run_client(), 0)
        self.assertEqual(len(self.posts()), 1)
        _, _, route, body = self.posts()[0]
        self.assertEqual(route, "/generation/image-to-image")
        self.assertEqual(body, {"input": "file_dummy_ui", "model": "seedream_v5", "size": "2K",
                                "output_format": "png", "watermark": False,
                                "prompt": self.prompt_file.read_text(encoding="utf-8").strip()})
        receipt = self.receipt()
        self.assertEqual(receipt["jobKind"], "image_to_image")
        self.assertEqual(receipt["route"], route)
        self.assertEqual(receipt["maximumCreditsPerKey"], 600)
        self.assertEqual(receipt["preflightBudget"], 30)
        self.assertFalse(receipt["visualAccepted"])
        self.assertFalse(receipt["productionAccepted"])
        self.assert_no_secret_output()

    def test_image_delivery_without_model_url_completes_as_owned_png(self):
        self.assertEqual(self.run_client(), 0)
        receipt = self.receipt()
        self.assertEqual(set(receipt["artifacts"]), {"image"})
        self.assertEqual(Path(receipt["artifacts"]["image"]["path"]), self.output / "image.png")
        self.assertEqual(len(self.download_calls), 1)
        self.assertEqual(self.download_calls[0][2:], (32 * 1024 * 1024, True))
        self.assertEqual((self.output / "image.png").read_bytes(), self.png)

    def test_model_and_rendered_preview_urls_do_not_change_ui_delivery(self):
        self.task_result["output"].update(model_url="https://example.invalid/unwanted.glb",
                                          rendered_image_url="https://example.invalid/unwanted-preview.png")
        self.assertEqual(self.run_client(), 0)
        self.assertEqual(len(self.download_calls), 1)
        self.assertEqual(self.download_calls[0][0], "https://example.invalid/ui.png")
        self.assertEqual(set(self.receipt()["artifacts"]), {"image"})

    def test_prompt_provenance_binds_file_bytes_path_and_submitted_character_count(self):
        self.prompt_file.write_bytes("  Đúng bố cục nguyên mẫu.\r\n".encode("utf-8"))
        self.assertEqual(self.run_client(), 0)
        prompt = self.receipt()["promptFile"]
        self.assertEqual(prompt["path"], self.prompt_file.relative_to(self.root).as_posix())
        self.assertEqual(prompt["sha256"], candidate.transport.sha256_file(self.prompt_file))
        self.assertEqual(prompt["characters"], len(self.prompt_file.read_text(encoding="utf-8").strip()))
        self.assertEqual(self.posts()[0][3]["prompt"], "Đúng bố cục nguyên mẫu.")

    def test_missing_prompt_stops_before_wallet_upload_or_generation(self):
        with self.assertRaises(candidate.transport.SafeFailure):
            self.run_client(prompt=False)
        self.assertFalse(self.balance_calls)
        self.assertFalse(self.upload_calls)
        self.assertFalse(self.api_calls)

    def test_empty_and_overlength_prompts_stop_before_any_api(self):
        for text in (" \r\n\t", "x" * 1025):
            with self.subTest(characters=len(text)):
                self.setUp()
                self.prompt_file.write_text(text, encoding="utf-8")
                with self.assertRaises(candidate.transport.SafeFailure):
                    self.run_client()
                self.assertFalse(self.balance_calls)
                self.assertFalse(self.api_calls)

    def test_prompt_character_limit_accepts1024_utf8_characters(self):
        self.prompt_file.write_text("đ" * 1024, encoding="utf-8")
        self.assertEqual(self.run_client(), 0)
        self.assertEqual(len(self.posts()[0][3]["prompt"]), 1024)

    def test_prompt_outside_workspace_and_prompt_on_model_profile_are_rejected(self):
        self.prompt_file = self.root.parent / "outside-reviewed-prompt.txt"
        with self.assertRaises(candidate.transport.SafeFailure):
            self.run_client()
        self.assertFalse(self.api_calls)
        self.setUp()
        with self.assertRaises(candidate.transport.SafeFailure):
            self.run_client(profile="high-quality")
        self.assertFalse(self.api_calls)

    def test_ui_credit_budget_reserves30_and_cannot_exceed600(self):
        self.prior(575)
        self.assertEqual(self.run_client(), 1)
        self.assertFalse(self.posts())
        self.assertFalse(self.upload_calls)
        self.assertFalse(self.ring.removed)
        self.assertEqual(self.receipt()["pipelineStatus"], "preflight")

    def test_exact600_reservation_boundary_is_allowed(self):
        self.prior(570)
        self.assertEqual(self.run_client(), 0)
        self.assertEqual(self.receipt()["previousRecordedCredits"], 570)
        self.assertEqual(len(self.posts()), 1)

    def test_positive_unaffordable_wallet_is_retained_and_no_job_is_submitted(self):
        self.balance = Decimal(29)
        self.assertEqual(self.run_client(), 1)
        self.assertFalse(self.posts())
        self.assertFalse(self.upload_calls)
        self.assertFalse(self.ring.removed)

    def test_ui_submission_ambiguity_is_preserved_and_never_retried(self):
        self.post_failure = candidate.ApiFailure()
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["pipelineStatus"], "submission_unknown_do_not_retry")
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse(self.ring.removed)

    def test_missing_generated_image_url_preserves_task_for_recovery(self):
        self.task_result["output"] = {}
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["pipelineStatus"], "downloading")
        self.assertEqual(self.receipt()["taskId"], "task_dummy_ui_01")
        self.assertEqual(len(self.posts()), 1)
        self.assert_no_secret_output()

    def test_image_recovery_is_get_only_uses_original_owner_and_creates_png(self):
        self.persisted()
        self.ring.members = [self.other_key, self.key]
        self.assertEqual(self.run_recovery(), 0)
        self.assertTrue(all(call[1] == "GET" and call[0] == self.secret for call in self.api_calls))
        self.assertEqual(set(self.receipt()["artifacts"]), {"image"})
        self.assertFalse(self.receipt()["recoveryUsesGenerationPost"])
        self.assertEqual((self.output / "image.png").read_bytes(), self.png)
        self.assertGreaterEqual(self.ring.refreshes, 3)
        self.assert_no_secret_output()

    def test_owned_png_hash_is_reused_without_any_delivery_request(self):
        self.persisted()
        image = self.output / "image.png"
        image.write_bytes(self.png)
        receipt = self.receipt()
        receipt["artifacts"]["image"] = {"path": str(image), "sha256": candidate.transport.sha256_file(image)}
        (self.output / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        self.assertEqual(self.run_recovery(), 0)
        self.assertFalse(self.download_calls)

    def test_unrelated_png_and_wrong_candidate_filename_are_rejected(self):
        for relative_path in ("unrelated.png", "ArtSource/P08/Tripo/UI/Dummy/candidate01/model.glb"):
            with self.subTest(relative_path=relative_path):
                self.setUp()
                self.persisted()
                unrelated = self.root / relative_path
                unrelated.write_bytes(self.png)
                receipt = self.receipt()
                receipt["artifacts"]["image"] = {"path": str(unrelated), "sha256": candidate.transport.sha256_file(unrelated)}
                (self.output / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaises(candidate.transport.SafeFailure):
                    self.run_recovery()
                self.assertEqual(unrelated.read_bytes(), self.png)
                self.assertFalse(self.download_calls)

    def test_partial_png_is_preserved_before_fresh_delivery(self):
        self.persisted(pipelineStatus="downloading")
        old = self.output / "image.png"
        old.write_bytes(b"\x89PNG\r\n\x1a\npartial_old_candidate")
        old_bytes = old.read_bytes()
        self.assertEqual(self.run_recovery(), 0)
        preserved = self.root / self.receipt()["preservedIncompleteDownloads"][0]
        self.assertEqual(preserved.read_bytes(), old_bytes)
        self.assertEqual(old.read_bytes(), self.png)
        self.assertEqual(len(self.download_calls), 1)


if __name__ == "__main__":
    unittest.main()
