"""Focused key lifecycle tests. All credentials are temporary dummy values."""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from io import BytesIO
import json
import os
from pathlib import Path
import pickle
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import keyring


class KeyringTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "dummy-keys.txt"
        self.path.write_bytes(b"dummy_alpha\r\ndummy_beta\r\n")
        self.ring = keyring.Keyring(self.path, retry_delay=0)

    def proof(self, key=None, balance=0, frozen=0, **kwargs):
        return keyring.VerifiedBalance.from_response(
            key or self.ring.select(), http_status=200,
            body={"code": 0, "data": {"balance": balance, "frozen": frozen}},
            endpoint=keyring.BALANCE_ENDPOINTS["v3"], **kwargs)

    def test_inventory_and_selection_are_secret_safe_deduplicated_and_fresh(self):
        self.path.write_bytes(b"# retained\r\n\n dummy_alpha \r\ndummy_beta\ndummy_alpha\r\n; retained\r// retained")
        inventory = self.ring.inventory()
        self.assertEqual((inventory.key_lines, inventory.unique_keys, inventory.duplicate_lines), (3, 2, 1))
        self.assertEqual((inventory.comment_lines, inventory.blank_lines), (3, 1))
        first, second = self.ring.keys()
        self.assertEqual(self.ring.select(after=first).fingerprint, second.fingerprint)
        self.assertEqual(self.ring.select(after=second).fingerprint, first.fingerprint)
        with self.path.open("ab") as stream:
            stream.write(b"\ndummy_gamma\r\n")
        self.assertEqual(self.ring.inventory().unique_keys, 3)
        third = self.ring.select(exclude_fingerprints=frozenset((first.fingerprint, second.fingerprint)))
        self.assertEqual(third.authentication_value(), "dummy_gamma")
        reports = repr((self.ring, self.ring.keys(), inventory, self.proof()))
        reports += json.dumps(inventory.summary())
        for value in ("dummy_alpha", "dummy_beta", "dummy_gamma"):
            self.assertNotIn(value, reports)
        with self.assertRaises(TypeError):
            pickle.dumps(first)

    def test_removal_preserves_bom_raw_line_endings_spaces_comments_and_other_duplicates(self):
        raw = b"\xef\xbb\xbf# heading\r\n dummy_alpha \r\n\r\ndummy_beta\ndummy_alpha\r; keep\rdummy_beta"
        self.path.write_bytes(raw)
        first = self.ring.select()
        result = self.ring.remove_confirmed_empty(first, self.proof(first))
        expected = b"\xef\xbb\xbf# heading\r\n\r\ndummy_beta\n; keep\rdummy_beta"
        self.assertEqual(self.path.read_bytes(), expected)
        self.assertEqual(result.removed_lines, 2)
        self.assertEqual(result.inventory.unique_keys, 1)
        self.assertEqual(result.inventory.duplicate_lines, 1)
        self.assertNotIn("dummy_alpha", repr(result))

    def test_utf16_bom_and_bytes_are_preserved(self):
        text = "# comment\r\n dummy_alpha \r\ndummy_beta\ndummy_beta"
        for encoding, bom in (("utf-16-le", b"\xff\xfe"), ("utf-16-be", b"\xfe\xff")):
            with self.subTest(encoding=encoding):
                self.path.write_bytes(bom + text.encode(encoding))
                key = self.ring.select()
                self.ring.remove_confirmed_empty(key, self.proof(key))
                self.assertEqual(self.path.read_bytes(), bom + "# comment\r\ndummy_beta\ndummy_beta".encode(encoding))

    def test_empty_file_remains_present_with_bom_and_comments(self):
        self.path.write_bytes(b"\xef\xbb\xbf# comment\r\ndummy_alpha\n")
        key = self.ring.select()
        self.assertIsNone(self.ring.rotate_confirmed_empty(key, self.proof(key)))
        self.assertTrue(self.path.is_file())
        self.assertEqual(self.path.read_bytes(), b"\xef\xbb\xbf# comment\r\n")

    def test_positive_unaffordable_frozen_stale_future_and_wrong_key_proofs_never_delete(self):
        original = self.path.read_bytes()
        first, second = self.ring.keys()
        proofs = [self.proof(first, balance=1), self.proof(first, frozen=100),
                  self.proof(first, observed_at=time.monotonic() - 61),
                  self.proof(first, observed_at=time.monotonic() + 5), self.proof(second)]
        for proof in proofs:
            with self.subTest(proof=repr(proof)):
                with self.assertRaises(keyring.KeyringError):
                    self.ring.remove_confirmed_empty(first, proof)
                self.assertEqual(self.path.read_bytes(), original)
        with self.assertRaises(keyring.KeyringError):
            self.ring.remove_confirmed_empty(first, None)

    def test_failed_http_api_codes_and_malformed_amounts_cannot_form_proof(self):
        key = self.ring.select()
        base = {"code": 0, "data": {"balance": 0, "frozen": 0}}
        for status in (401, 403, 429, 500, True):
            with self.subTest(status=status), self.assertRaises(keyring.BalanceCheckError):
                keyring.VerifiedBalance.from_response(key, http_status=status, body=base,
                                                     endpoint=keyring.BALANCE_ENDPOINTS["v3"])
        for code in (2010, 1001, True, 0.0, "0", None):
            with self.subTest(code=code), self.assertRaises(keyring.BalanceCheckError):
                keyring.VerifiedBalance.from_response(key, http_status=200,
                                                     body={**base, "code": code},
                                                     endpoint=keyring.BALANCE_ENDPOINTS["v3"])
        for field in ("balance", "frozen"):
            for value in (True, None, -1, "nan", "Infinity", "-Infinity", "dummy_alpha", {}):
                with self.subTest(field=field, value=value), self.assertRaises(keyring.BalanceCheckError):
                    keyring.VerifiedBalance.from_response(key, http_status=200,
                        body={"code": 0, "data": {"balance": 0, "frozen": 0, field: value}},
                        endpoint=keyring.BALANCE_ENDPOINTS["v3"])
        with self.assertRaises(keyring.BalanceCheckError):
            keyring.VerifiedBalance.from_response(key, http_status=200, body=base,
                                                 endpoint="https://example.invalid/account/balance")
        self.assertEqual(self.path.read_bytes(), b"dummy_alpha\r\ndummy_beta\r\n")

    def test_proof_is_immutable(self):
        proof = self.proof(balance=1)
        with self.assertRaises(FrozenInstanceError):
            proof.balance = 0

    def test_retry_rereads_and_retains_append_before_exclusive_acquisition(self):
        key = self.ring.select()
        attempts = []
        @contextmanager
        def retrying(path):
            attempts.append(1)
            if len(attempts) == 1:
                with path.open("ab") as stream:
                    stream.write(b"dummy_gamma\n")
                raise keyring.KeyFileBusy("Temporary sharing violation.")
            with keyring._exclusive_file(path) as stream:
                yield stream
        ring = keyring.Keyring(self.path, retry_delay=0, exclusive_opener=retrying)
        result = ring.remove_confirmed_empty(key, self.proof(key))
        self.assertEqual(len(attempts), 2)
        self.assertEqual(result.inventory.unique_keys, 2)
        self.assertEqual(self.path.read_bytes(), b"dummy_beta\r\ndummy_gamma\n")

    def test_rotation_does_a_fresh_post_transaction_read(self):
        key = self.ring.select()
        @contextmanager
        def append_on_release(path):
            with keyring._exclusive_file(path) as stream:
                yield stream
            with path.open("ab") as stream:
                stream.write(b"dummy_gamma\n")
        ring = keyring.Keyring(self.path, retry_delay=0, exclusive_opener=append_on_release)
        beta = self.ring.keys()[1]
        next_key = ring.rotate_confirmed_empty(key, self.proof(key),
                                               exclude_fingerprints=frozenset((beta.fingerprint,)))
        self.assertEqual(next_key.authentication_value(), "dummy_gamma")

    def test_failed_acquisition_keeps_every_byte(self):
        key = self.ring.select()
        original = self.path.read_bytes()
        calls = []
        @contextmanager
        def busy(path):
            calls.append(1)
            raise keyring.KeyFileBusy("Dummy writer owns the file.")
            yield  # pragma: no cover
        ring = keyring.Keyring(self.path, lock_attempts=3, retry_delay=0, exclusive_opener=busy)
        with self.assertRaises(keyring.KeyFileBusy):
            ring.remove_confirmed_empty(key, self.proof(key))
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.path.read_bytes(), original)

    def test_proof_freshness_is_rechecked_after_acquisition(self):
        key = self.ring.select()
        with patch.object(keyring.time, "monotonic", return_value=100):
            proof = self.proof(key)
        original = self.path.read_bytes()
        @contextmanager
        def late(path):
            with keyring._exclusive_file(path) as stream:
                with patch.object(keyring.time, "monotonic", return_value=161):
                    yield stream
        ring = keyring.Keyring(self.path, retry_delay=0, exclusive_opener=late)
        with patch.object(keyring.time, "monotonic", return_value=100):
            with self.assertRaises(keyring.KeyringError):
                ring.remove_confirmed_empty(key, proof)
        self.assertEqual(self.path.read_bytes(), original)

    def test_write_failure_restores_exact_original_without_secret_temp_file(self):
        key = self.ring.select()
        original = self.path.read_bytes()
        write_all = keyring._write_all
        calls = []
        def flaky(stream, value):
            calls.append(1)
            if len(calls) == 1:
                stream.seek(0)
                stream.write(b"xx")
                stream.truncate(2)
                stream.flush()
                raise OSError("Dummy credential dummy_alpha should not appear in the safe error.")
            return write_all(stream, value)
        with patch.object(keyring, "_write_all", side_effect=flaky):
            with self.assertRaises(keyring.KeyringError) as context:
                self.ring.remove_confirmed_empty(key, self.proof(key))
        self.assertNotIn("dummy_alpha", str(context.exception))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [self.path])

    def test_rollback_failure_is_a_sanitized_stop_condition(self):
        key = self.ring.select()
        with patch.object(keyring, "_write_all", side_effect=OSError("dummy_alpha")):
            with self.assertRaisesRegex(keyring.KeyringError, "stop all key mutations") as context:
                self.ring.remove_confirmed_empty(key, self.proof(key))
        self.assertNotIn("dummy_alpha", str(context.exception))

    @unittest.skipUnless(os.name == "nt", "Native Windows share-mode behavior")
    def test_native_windows_exclusive_transaction_blocks_then_preserves_external_append(self):
        key = self.ring.select()
        attempted = threading.Event()
        denied = threading.Event()
        done = threading.Event()
        failures = []
        def writer():
            attempted.set()
            for _ in range(200):
                try:
                    with self.path.open("ab") as stream:
                        stream.write(b"dummy_gamma\r\n")
                    done.set()
                    return
                except PermissionError:
                    denied.set()
                    time.sleep(0.005)
                except Exception:
                    failures.append("Unexpected append failure.")
                    return
            failures.append("Append did not acquire the file after release.")
        thread = threading.Thread(target=writer)
        @contextmanager
        def controlled(path):
            with keyring._exclusive_file(path) as stream:
                thread.start()
                self.assertTrue(attempted.wait(1))
                self.assertTrue(denied.wait(1))
                self.assertFalse(done.is_set())
                yield stream
        ring = keyring.Keyring(self.path, retry_delay=0, exclusive_opener=controlled)
        ring.remove_confirmed_empty(key, self.proof(key))
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertFalse(failures)
        self.assertTrue(done.is_set())
        self.assertEqual(self.path.read_bytes(), b"dummy_beta\r\ndummy_gamma\r\n")

    def test_missing_and_invalid_file_errors_do_not_expose_key_bytes(self):
        self.path.write_bytes(b"dummy_alpha bad\n")
        with self.assertRaises(keyring.KeyFileFormatError) as context:
            self.ring.select()
        self.assertNotIn("dummy_alpha", str(context.exception))
        self.path.write_bytes(b"\xff invalid")
        with self.assertRaises(keyring.KeyFileFormatError):
            self.ring.select()
        missing = keyring.Keyring(Path(self.directory.name) / "does-not-exist")
        with self.assertRaises(keyring.KeyringError):
            missing.select()
        self.assertEqual(len(list(Path(self.directory.name).iterdir())), 1)

    def test_wallet_transport_has_only_get_and_numeric_secret_safe_error_details(self):
        key = self.ring.select()
        class Response(BytesIO):
            status = 200
        class Opener:
            def __init__(self, error=None):
                self.error = error
                self.requests = []
            def open(self, request, timeout):
                self.requests.append(request)
                if self.error:
                    raise self.error
                return Response(b'{"code":0,"data":{"balance":600,"frozen":0}}')
        opener = Opener()
        with patch.object(keyring, "build_opener", return_value=opener):
            result = keyring.fetch_balance(key)
        self.assertEqual(result.balance, 600)
        self.assertEqual(opener.requests[0].get_method(), "GET")
        self.assertEqual(opener.requests[0].full_url, keyring.BALANCE_ENDPOINTS["v3"])
        for error in (URLError("dummy_alpha"), TimeoutError("dummy_alpha"),
                      HTTPError("https://example.invalid", 403, "dummy_alpha", {},
                                BytesIO(b'{"code":2010,"message":"dummy_alpha"}'))):
            with patch.object(keyring, "build_opener", return_value=Opener(error)):
                with self.assertRaises(keyring.BalanceCheckError) as context:
                    keyring.fetch_balance(key)
                self.assertNotIn("dummy_alpha", json.dumps(context.exception.summary()))
                if isinstance(error, HTTPError):
                    self.assertEqual(context.exception.api_code, 2010)
                    self.assertEqual(context.exception.http_status, 403)
        redirect = keyring._NoRedirect()
        with self.assertRaises(keyring.BalanceCheckError):
            redirect.redirect_request(None, None, 302, "dummy_alpha", {}, "https://example.invalid")
        self.assertEqual(self.path.read_bytes(), b"dummy_alpha\r\ndummy_beta\r\n")


if __name__ == "__main__":
    unittest.main()
