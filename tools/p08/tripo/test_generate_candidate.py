"""Mocked lifecycle controls. No real key file, HTTP request or paid operation."""
from contextlib import redirect_stdout, redirect_stderr
from decimal import Decimal
import importlib.util
from io import StringIO
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import keyring


# Install before importing the production modules. Adapter changes must fail a
# test rather than letting dummy credentials reach any remote endpoint.
_connect_guard = patch("socket.socket.connect", side_effect=AssertionError("Offline test blocked a network connection."))
_connect_ex_guard = patch("socket.socket.connect_ex", side_effect=AssertionError("Offline test blocked a network connection."))
_connect_mock = _connect_guard.start()
_connect_ex_mock = _connect_ex_guard.start()


def tearDownModule():
    _connect_ex_guard.stop()
    _connect_guard.stop()


MODULE_PATH = Path(__file__).with_name("generate_candidate.py")
spec = importlib.util.spec_from_file_location("generate_candidate_under_test", MODULE_PATH)
candidate = importlib.util.module_from_spec(spec)
sys.modules["generate_candidate"] = candidate
spec.loader.exec_module(candidate)
recover_spec = importlib.util.spec_from_file_location("recover_candidate_under_test", MODULE_PATH.with_name("recover_candidate.py"))
recovery = importlib.util.module_from_spec(recover_spec)
recover_spec.loader.exec_module(recovery)
api_module = sys.modules["api"]


class _Inventory:
    def __init__(self, keys):
        self.keys = keys

    def summary(self):
        return {"key_lines": len(self.keys), "unique_keys": len(self.keys),
                "duplicate_lines": 0, "comment_lines": 0, "blank_lines": 0,
                "fingerprints": [key.fingerprint for key in self.keys]}


class _Ring:
    def __init__(self, keys):
        self._keys = list(keys)
        self.removed = []
        self.refreshes = 0
        self.on_remove = None

    def inventory(self):
        self.refreshes += 1
        return _Inventory(self._keys)

    def keys(self):
        self.refreshes += 1
        return tuple(self._keys)

    def select(self, *, exclude_fingerprints=frozenset(), after=None):
        self.refreshes += 1
        return next((key for key in self._keys if key.fingerprint not in exclude_fingerprints), None)

    def remove_confirmed_empty(self, key, proof):
        proof.require_empty(key)
        self.removed.append(key.fingerprint)
        self._keys = [existing for existing in self._keys if existing.fingerprint != key.fingerprint]
        if self.on_remove:
            self.on_remove(self)
        return keyring.RemovalResult(key.fingerprint, 1, keyring.Inventory(
            len(self._keys), len(self._keys), 0, 0, 0, tuple(key.fingerprint for key in self._keys)))


class GenerationLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.input = self.root / "input.png"
        self.input.write_bytes(b"\x89PNG\r\n\x1a\ndummy-reviewed-image")
        self.reference = self.root / "reference.png"
        self.reference.write_bytes(b"\x89PNG\r\n\x1a\ndummy-locked-concept")
        self.output = self.root / "ArtSource/P08/Tripo/dummy/candidate01"
        self.secrets = ("tsk_dummy_alpha_credential", "tsk_dummy_beta_credential")
        self.keys = [keyring.KeyRef(value) for value in self.secrets]
        self.ring = _Ring(self.keys[:1])
        self.wallets = {key.fingerprint: (Decimal(600), Decimal(0)) for key in self.keys}
        self.balance_calls = []
        self.api_calls = []
        self.upload_calls = []
        self.download_calls = []
        self.post_result = {"task_id": "task_mock_01"}
        self.poll_result = {"status": "success", "progress": 100, "credits_consumed": 80,
                            "output": {"model_url": "https://example.invalid/model.glb"}}
        self.poll_failure = None
        self.post_failure = None
        self.download_failure = None
        self.balance_failures = set()
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.network_call_count = (_connect_mock.call_count, _connect_ex_mock.call_count)

    def balance(self, key, *, version="v3"):
        self.balance_calls.append(key.fingerprint)
        if key.fingerprint in self.balance_failures:
            raise keyring.BalanceCheckError("The wallet request failed or timed out.")
        available, frozen = self.wallets[key.fingerprint]
        return keyring.VerifiedBalance.from_response(key, http_status=200,
            body={"code": 0, "data": {"balance": str(available), "frozen": str(frozen)}},
            endpoint=keyring.BALANCE_ENDPOINTS[version])

    def upload(self, key, image):
        self.upload_calls.append((key, image))
        return "file_token_mock"

    def api(self, key, method, route, body=None):
        self.api_calls.append((key, method, route, body))
        if method == "POST":
            if self.post_failure:
                raise self.post_failure
            return self.post_result
        if self.poll_failure:
            raise self.poll_failure
        return self.poll_result

    def download(self, url, path, byte_limit, *, preview=False):
        self.download_calls.append((url, path, byte_limit, preview))
        if self.download_failure:
            raise self.download_failure
        path.write_bytes(b"glTF-dummy-model")
        return {"path": str(path), "sha256": candidate.transport.sha256_file(path), "bytes": path.stat().st_size}

    def run_client(self, extra_args=()):
        args = ["generate_candidate.py", "--input", str(self.input), "--reference", str(self.reference),
                "--out", str(self.output), "--key-file", str(self.root / "NEVER_READ_REAL_KEYS.txt"),
                "--profile", "high-quality", *extra_args]
        with patch.object(candidate, "ROOT", self.root), \
             patch.object(candidate, "Keyring", return_value=self.ring), \
             patch.object(candidate, "fetch_balance", side_effect=self.balance), \
             patch.object(candidate.transport, "upload_image", side_effect=self.upload), \
             patch.object(candidate, "api_call", side_effect=self.api), \
             patch.object(candidate.transport, "download_asset", side_effect=self.download), \
             patch.object(candidate.time, "sleep"), patch.object(sys, "argv", args), \
             redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            try:
                return candidate.run()
            finally:
                self.assertEqual((_connect_mock.call_count, _connect_ex_mock.call_count), self.network_call_count,
                                 "A mocked test attempted an unexpected network connection.")

    def receipt(self):
        return json.loads((self.output / "receipt.json").read_text(encoding="utf-8"))

    def posts(self):
        return [call for call in self.api_calls if call[1] == "POST"]

    def old_receipt(self, value):
        path = self.root / "ArtSource/P08/Tripo/prior/receipt.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"keyFingerprint": self.keys[0].fingerprint, **value}), encoding="utf-8")
        return path

    def assert_no_secret_output(self):
        text = self.stdout.getvalue() + self.stderr.getvalue()
        if self.output.exists():
            for path in self.output.rglob("*.json"):
                text += path.read_text(encoding="utf-8")
        for secret in self.secrets:
            self.assertNotIn(secret, text)

    def test_success_remains_unaccepted_and_never_persists_credentials(self):
        self.assertEqual(self.run_client(), 0)
        receipt = self.receipt()
        self.assertEqual(receipt["pipelineStatus"], "completed")
        self.assertFalse(receipt["visualAccepted"])
        self.assertFalse(receipt["productionAccepted"])
        self.assertEqual(receipt["creditsConsumed"], 80)
        self.assertEqual(len(self.posts()), 1)
        self.assertGreaterEqual(self.ring.refreshes, 4)
        self.assert_no_secret_output()

    def test_ambiguous_post_outcome_never_retries_or_rotates_or_deletes(self):
        self.ring._keys = self.keys
        self.post_failure = candidate.ApiFailure()
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["pipelineStatus"], "submission_unknown_do_not_retry")
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.upload_calls), 1)
        self.assertFalse(self.ring.removed)
        self.assert_no_secret_output()

    def test_unexpected_secret_bearing_post_exception_is_redacted_and_reservation_is_retained(self):
        self.post_failure = RuntimeError(self.secrets[0])
        self.assertEqual(self.run_client(), 1)
        self.assertIn(self.receipt()["pipelineStatus"], ("submission_pending", "submission_unknown_do_not_retry"))
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse(self.ring.removed)
        self.assert_no_secret_output()

    def test_missing_task_id_is_unknown_and_does_not_resubmit(self):
        self.post_result = {"task_id": "invalid / task"}
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["pipelineStatus"], "submission_unknown_do_not_retry")
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse(self.ring.removed)

    def test_code2010_is_rejection_and_never_credit_depletion_evidence(self):
        self.ring._keys = self.keys
        self.post_failure = candidate.ApiFailure(http_status=403, code=2010, definitive_rejection=True)
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["pipelineStatus"], "submission_rejected")
        self.assertEqual(self.receipt()["keyAttempts"][-1]["submissionRejection"]["code"], 2010)
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse(self.ring.removed)

    def test_unaffordable_positive_and_frozen_keys_are_retained_for_future_work(self):
        for wallet in ((Decimal(10), Decimal(0)), (Decimal(600), Decimal(20))):
            with self.subTest(wallet=wallet):
                self.setUp()
                self.ring._keys = self.keys
                self.wallets[self.keys[0].fingerprint] = wallet
                self.assertEqual(self.run_client(), 0)
                self.assertEqual(self.receipt()["keyFingerprint"], self.keys[1].fingerprint)
                self.assertFalse(self.ring.removed)
                self.assertEqual(len(self.posts()), 1)
                self.assertEqual(len(self.receipt()["keyAttempts"]), 2)
                self.assert_no_secret_output()

    def test_confirmed_empty_removal_then_new_append_selection_is_fresh(self):
        self.wallets[self.keys[0].fingerprint] = (Decimal(0), Decimal(0))
        self.ring.on_remove = lambda ring: ring._keys.append(self.keys[1])
        self.assertEqual(self.run_client(), 0)
        self.assertEqual(self.ring.removed, [self.keys[0].fingerprint])
        self.assertEqual(self.receipt()["keyFingerprint"], self.keys[1].fingerprint)
        self.assertEqual(len(self.posts()), 1)
        self.assert_no_secret_output()

    def test_unknown_wallet_is_never_deleted_and_another_current_key_can_be_selected(self):
        self.ring._keys = self.keys
        self.balance_failures.add(self.keys[0].fingerprint)
        self.assertEqual(self.run_client(), 0)
        self.assertEqual(self.receipt()["keyFingerprint"], self.keys[1].fingerprint)
        self.assertFalse(self.ring.removed)
        self.assertTrue(self.receipt()["keyAttempts"][0]["balanceUnavailable"])

    def test_no_eligible_key_stops_before_upload_or_post(self):
        self.wallets[self.keys[0].fingerprint] = (Decimal(119), Decimal(0))
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["pipelineStatus"], "preflight")
        self.assertFalse(self.posts())
        self.assertFalse(self.upload_calls)
        self.assertFalse(self.ring.removed)

    def test_existing_unsettled_task_blocks_fresh_generation(self):
        for state in ("submission_pending", "submission_unknown_do_not_retry", "task_submitted", "downloading"):
            with self.subTest(state=state):
                self.setUp()
                self.old_receipt({"pipelineStatus": state, "taskId": "task_prior_01", "creditsConsumed": 0})
                self.assertEqual(self.run_client(), 1)
                self.assertFalse(self.posts())
                self.assertFalse(self.upload_calls)
                self.assertFalse(self.ring.removed)

    def test_recorded_consumption_plus_budget_cannot_exceed600(self):
        self.old_receipt({"pipelineStatus": "completed", "creditsConsumed": 500})
        self.assertEqual(self.run_client(), 1)
        self.assertFalse(self.posts())
        self.assertFalse(self.upload_calls)
        self.assertFalse(self.ring.removed)

    def test_negative_prior_consumption_must_not_reduce_the600_cap(self):
        self.old_receipt({"pipelineStatus": "completed", "creditsConsumed": -500})
        self.assertEqual(self.run_client(), 1)
        self.assertFalse(self.posts())
        self.assertFalse(self.upload_calls)

    def test_invalid_prior_credit_values_never_reach_submission(self):
        for value in (True, None, "NaN", "Infinity", "-Infinity", "not_a_credit", {}):
            with self.subTest(value=value):
                self.setUp()
                self.old_receipt({"pipelineStatus": "completed", "creditsConsumed": value})
                self.assertEqual(self.run_client(), 1)
                self.assertFalse(self.posts())
                self.assertFalse(self.upload_calls)
                self.assertFalse(self.ring.removed)

    def test_invalid_live_credit_values_preserve_task_and_block_completion(self):
        for value in (True, -1, "NaN", "Infinity", "not_a_credit"):
            with self.subTest(value=value):
                self.setUp()
                self.poll_result["credits_consumed"] = value
                self.assertEqual(self.run_client(), 1)
                self.assertEqual(self.receipt()["taskId"], "task_mock_01")
                self.assertEqual(self.receipt()["pipelineStatus"], "task_submitted")
                self.assertEqual(len(self.posts()), 1)
                self.assertFalse(self.download_calls)
                self.assert_no_secret_output()

    def test_polling_unavailable_preserves_saved_task_and_never_posts_again(self):
        self.poll_failure = candidate.ApiFailure()
        self.assertEqual(self.run_client(), 1)
        receipt = self.receipt()
        self.assertEqual(receipt["taskId"], "task_mock_01")
        self.assertEqual(receipt["pipelineStatus"], "task_submitted")
        self.assertTrue((self.output / "task.json").is_file())
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.api_calls), 8)
        self.assertFalse(self.ring.removed)
        self.assert_no_secret_output()

    def test_unknown_poll_status_preserves_task_and_does_not_resubmit(self):
        self.poll_result = {"status": "unexpected", "progress": 0}
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["taskId"], "task_mock_01")
        self.assertEqual(self.receipt()["pipelineStatus"], "task_submitted")
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse(self.ring.removed)

    def test_failed_download_preserves_task_and_pending_download_reservation(self):
        self.download_failure = candidate.transport.SafeFailure("Artifact download failed; signed URL was not logged.")
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["taskId"], "task_mock_01")
        self.assertEqual(self.receipt()["pipelineStatus"], "downloading")
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse(self.ring.removed)
        self.assert_no_secret_output()

    def test_failure_status_retains_task_and_never_auto_retries(self):
        self.poll_result = {"status": "failed", "progress": 30, "credits_consumed": 0}
        self.assertEqual(self.run_client(), 1)
        self.assertEqual(self.receipt()["pipelineStatus"], "task_terminal_failure")
        self.assertEqual(self.receipt()["taskId"], "task_mock_01")
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse(self.ring.removed)

    def test_profiles_keep_parts_compatible_and_requested_texture_detail_explicit(self):
        parts, _, _ = candidate.PROFILES["high-quality-parts"]
        self.assertTrue(parts["generate_parts"])
        self.assertFalse(parts["texture"])
        self.assertFalse(parts["pbr"])
        quality, _, _ = candidate.PROFILES["high-quality"]
        self.assertFalse(quality["generate_parts"])
        self.assertTrue(quality["texture"])
        self.assertTrue(quality["pbr"])
        self.assertEqual(quality["geometry_quality"], "detailed")
        self.assertEqual(quality["texture_quality"], "extreme")
        self.assertEqual(quality["texture_version"], "v3.5-20260815")

    def test_checkout_reservation_blocks_another_client_and_releases_after_failure(self):
        with patch.object(candidate, "ROOT", self.root):
            with self.assertRaisesRegex(RuntimeError, "Dummy job failure"):
                with candidate.exclusive_job():
                    with self.assertRaises(candidate.transport.SafeFailure):
                        with candidate.exclusive_job():
                            self.fail("A second client acquired the reservation.")
                    raise RuntimeError("Dummy job failure")
            with candidate.exclusive_job():
                pass
        self.assertFalse(self.api_calls)


class RecoveryLifecycleTests(GenerationLifecycleTests):
    # Share fixtures only; unittest would otherwise rerun all generation cases
    # through inheritance. ``load_tests`` below chooses the recover_* controls.
    def persisted_receipt(self, **updates):
        self.output.mkdir(parents=True)
        receipt = {"schema": "racing-bois.tripo-candidate.v2", "taskId": "task_mock_01",
                   "keyFingerprint": self.keys[0].fingerprint, "pipelineStatus": "task_submitted",
                   "status": "unaccepted", "visualAccepted": False, "productionAccepted": False,
                   "artifacts": {}, **updates}
        (self.output / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        return receipt

    def run_recovery(self):
        args = ["recover_candidate.py", str(self.output), "--key-file", str(self.root / "NEVER_READ_REAL_KEYS.txt")]
        with patch.object(candidate, "ROOT", self.root), patch.object(recovery, "ROOT", self.root), \
             patch.object(recovery, "Keyring", return_value=self.ring), \
             patch.object(recovery, "fetch_balance", side_effect=self.balance), \
             patch.object(recovery, "api_call", side_effect=self.api), \
             patch.object(recovery.transport, "download_asset", side_effect=self.download), \
             patch.object(recovery.time, "sleep"), patch.object(sys, "argv", args), \
             redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            try:
                return recovery.main()
            finally:
                self.assertEqual((_connect_mock.call_count, _connect_ex_mock.call_count), self.network_call_count)
                self.assertFalse(self.posts(), "Recovery must issue only GET, never a generation POST.")

    def recover_success_uses_original_key_get_only_and_remains_unaccepted(self):
        self.persisted_receipt(failure="A prior polling failure.")
        self.ring._keys = [self.keys[1], self.keys[0]]
        self.assertEqual(self.run_recovery(), 0)
        self.assertTrue(self.api_calls)
        self.assertTrue(all(call[0] == self.secrets[0] and call[1] == "GET" for call in self.api_calls))
        receipt = self.receipt()
        self.assertEqual(receipt["pipelineStatus"], "completed")
        self.assertFalse(receipt["recoveryUsesGenerationPost"])
        self.assertFalse(receipt["productionAccepted"])
        self.assertFalse(receipt["visualAccepted"])
        self.assertNotIn("failure", receipt)
        self.assert_no_secret_output()

    def recover_missing_key_stops_before_any_task_request(self):
        self.persisted_receipt()
        self.ring._keys = self.keys[1:]
        with self.assertRaises(candidate.transport.SafeFailure):
            self.run_recovery()
        self.assertFalse(self.api_calls)
        self.assertFalse(self.download_calls)

    def recover_invalid_task_id_stops_before_any_task_request(self):
        for task_id in ("../account/balance", "task / invalid", "x" * 129):
            with self.subTest(task_id=task_id):
                self.setUp()
                self.persisted_receipt(taskId=task_id)
                with self.assertRaises(candidate.transport.SafeFailure):
                    self.run_recovery()
                self.assertFalse(self.api_calls)

    def recover_partial_download_is_preserved_before_retry(self):
        self.persisted_receipt(pipelineStatus="downloading")
        incomplete = self.output / "model.glb"
        incomplete.write_bytes(b"glTF-partial-before-recovery")
        original = incomplete.read_bytes()
        self.assertEqual(self.run_recovery(), 0)
        receipt = self.receipt()
        preserved = self.root / receipt["preservedIncompleteDownloads"][0]
        self.assertEqual(preserved.read_bytes(), original)
        self.assertEqual(incomplete.read_bytes(), b"glTF-dummy-model")
        self.assertEqual(len(self.download_calls), 1)

    def recover_owned_complete_artifact_hash_is_reused_without_redownload(self):
        self.persisted_receipt(pipelineStatus="downloading")
        model = self.output / "model.glb"
        model.write_bytes(b"glTF-owned-complete-model")
        receipt = self.receipt()
        receipt["artifacts"]["model"] = {"path": str(model), "sha256": candidate.transport.sha256_file(model)}
        (self.output / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        self.assertEqual(self.run_recovery(), 0)
        self.assertFalse(self.download_calls)
        self.assertEqual(model.read_bytes(), b"glTF-owned-complete-model")

    def recover_unrelated_artifact_must_not_substitute_for_the_candidate_model(self):
        self.persisted_receipt(pipelineStatus="downloading")
        unrelated = self.root / "unrelated.glb"
        unrelated.write_bytes(b"glTF-unrelated-source")
        original = unrelated.read_bytes()
        receipt = self.receipt()
        receipt["artifacts"]["model"] = {"path": str(unrelated), "sha256": candidate.transport.sha256_file(unrelated)}
        (self.output / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        try:
            result = self.run_recovery()
        except candidate.transport.SafeFailure:
            result = 1
        self.assertEqual(unrelated.read_bytes(), original)
        if result == 0:
            self.assertEqual(len(self.download_calls), 1)
            self.assertEqual(Path(self.receipt()["artifacts"]["model"]["path"]), self.output / "model.glb")
        else:
            self.assertFalse(self.download_calls)

    def recover_unknown_status_preserves_task_and_does_not_delete_key(self):
        self.persisted_receipt()
        self.poll_result = {"status": "unknown"}
        with self.assertRaises(candidate.transport.SafeFailure):
            self.run_recovery()
        self.assertEqual(self.receipt()["taskId"], "task_mock_01")
        self.assertFalse(self.ring.removed)


class ApiTransportTests(unittest.TestCase):
    secret = "tsk_dummy_transport_secret"

    def setUp(self):
        self.network_calls = (_connect_mock.call_count, _connect_ex_mock.call_count)

    def tearDown(self):
        self.assertEqual((_connect_mock.call_count, _connect_ex_mock.call_count), self.network_calls)

    def call(self, payload=None, *, status=200, error=None):
        class Response(BytesIO):
            pass
        response = Response(payload if payload is not None else b'{"code":0,"data":{"task_id":"task_dummy"}}')
        response.status = status
        class Opener:
            calls = 0
            def open(self, request, timeout):
                self.calls += 1
                if error is not None:
                    raise error
                return response
        opener = Opener()
        with patch.object(api_module, "build_opener", return_value=opener):
            try:
                return api_module.api_call(self.secret, "POST", "/generation/image-to-model", {"input": "dummy_token"})
            finally:
                self.assertEqual(opener.calls, 1, "The transport must never retry a submission.")

    def test_definitive_rejections_report_numeric_fields_without_vendor_or_auth_text(self):
        for status in (200, 400, 401, 403, 409, 422, 429):
            with self.subTest(status=status):
                body = json.dumps({"code": 2010, "message": self.secret, "suggestion": self.secret}).encode()
                error = HTTPError("https://example.invalid", status, self.secret, {}, BytesIO(body)) if status != 200 else None
                with self.assertRaises(api_module.ApiFailure) as context:
                    self.call(body, status=status, error=error)
                self.assertTrue(context.exception.definitive_rejection)
                self.assertEqual(context.exception.code, 2010)
                self.assertNotIn(self.secret, str(context.exception) + json.dumps(context.exception.summary()))

    def test_network_timeouts_redirects_and_server_errors_are_ambiguous(self):
        for error in (URLError(self.secret), TimeoutError(self.secret),
                      HTTPError("https://example.invalid", 500, self.secret, {}, BytesIO(b'{"code":1001}'))):
            with self.subTest(error=type(error).__name__), self.assertRaises(api_module.ApiFailure) as context:
                self.call(error=error)
            self.assertFalse(context.exception.definitive_rejection)
            self.assertNotIn(self.secret, str(context.exception))
        with self.assertRaises(api_module.ApiFailure) as context:
            api_module.NoRedirect().redirect_request(None, None, 302, self.secret, {}, "https://example.invalid")
        self.assertFalse(context.exception.definitive_rejection)

    def test_invalid_oversized_or_nonobject_success_is_ambiguous(self):
        for payload in (b"not json", b"[]", b'{"code":false,"data":{}}', b'{"code":0,"data":[]}',
                        b'{"code":0}', b"x" * (1024 * 1024 + 1)):
            with self.subTest(size=len(payload)), self.assertRaises(api_module.ApiFailure) as context:
                self.call(payload)
            self.assertFalse(context.exception.definitive_rejection)

    def test_valid_success_returns_task_metadata(self):
        self.assertEqual(self.call(), {"task_id": "task_dummy"})

    def test_failed_http_error_body_read_is_ambiguous_and_secret_safe(self):
        secret = self.secret
        class BrokenBody(BytesIO):
            def read(self, *args):
                raise TimeoutError(secret)
        error = HTTPError("https://example.invalid", 403, secret, {}, BrokenBody())
        with self.assertRaises(api_module.ApiFailure) as context:
            self.call(error=error)
        self.assertFalse(context.exception.definitive_rejection)
        self.assertNotIn(secret, str(context.exception) + json.dumps(context.exception.summary()))


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(GenerationLifecycleTests))
    suite.addTests(loader.loadTestsFromTestCase(ApiTransportTests))
    for name in sorted(name for name in dir(RecoveryLifecycleTests) if name.startswith("recover_")):
        suite.addTest(RecoveryLifecycleTests(name))
    return suite


if __name__ == "__main__":
    unittest.main()
