"""Secret-safe Tripo key selection and confirmed-empty key removal.

Only ``fetch_balance`` issues a request, and it is a read-only GET to an exact
official endpoint. The generation client owns task submission, task recovery and
the user's 600-credit per-key consumption cap; wallet balances alone cannot prove
whether a credit was free or purchased. A positive, unaffordable balance, 401,
429, code 2010, malformed response or network error never permits deletion.

Selection and rotation always reload the file. Removal reads the latest bytes
under a Windows share-mode-zero handle, so an external append either completes
before that read and is retained, or waits until the transaction finishes. The
entire read/compare/write/flush transaction is exclusive, with rollback on write
failure. It does not create a second secret-bearing file. This is atomic with
respect to ordinary Windows file readers/writers; it is not a power-loss-safe
filesystem transaction. The POSIX fallback uses an advisory lock and requires
other writers to cooperate. No key file is unlinked or replaced.

Official documentation checked 2026-09-30:
https://platform.tripo3d.ai/docs/wallet
https://developers.tripo3d.ai/en/docs/account
https://developers.tripo3d.ai/en/docs/billing
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import BinaryIO, Callable, Iterator, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


BALANCE_ENDPOINTS = {
    "v2": "https://api.tripo3d.ai/v2/openapi/user/balance",
    "v3": "https://openapi.tripo3d.ai/v3/account/balance",
}
MAX_FILE_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
MAX_PROOF_AGE_SECONDS = 60.0


class KeyringError(Exception):
    """Only constant, secret-free messages are exposed to the caller."""


class KeyFileBusy(KeyringError):
    pass


class KeyFileFormatError(KeyringError):
    pass


class BalanceCheckError(KeyringError):
    def __init__(self, reason: str, *, http_status: int | None = None,
                 api_code: int | None = None) -> None:
        super().__init__(reason)
        self.http_status = http_status
        self.api_code = api_code

    def summary(self) -> dict:
        return {"verified": False, "reason": str(self),
                "http_status": self.http_status, "api_code": self.api_code}


class KeyRef:
    """A credential held in memory. repr/str contain only an opaque digest."""
    __slots__ = ("__value", "fingerprint")

    def __init__(self, value: str) -> None:
        if not value or not value.isascii() or any(character.isspace() or ord(character) < 32
                            or ord(character) == 127 for character in value):
            raise KeyFileFormatError("A key line contains invalid whitespace or controls.")
        self.__value = value
        self.fingerprint = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    def authentication_value(self) -> str:
        """For an Authorization header only; never print, serialize or log it."""
        return self.__value

    def __repr__(self) -> str:
        return f"KeyRef(fingerprint={self.fingerprint!r})"

    __str__ = __repr__

    def __reduce_ex__(self, protocol: int):
        raise TypeError("Credentials cannot be pickled.")


@dataclass(frozen=True)
class Inventory:
    key_lines: int
    unique_keys: int
    duplicate_lines: int
    comment_lines: int
    blank_lines: int
    fingerprints: tuple[str, ...]

    def summary(self) -> dict:
        return {"key_lines": self.key_lines, "unique_keys": self.unique_keys,
                "duplicate_lines": self.duplicate_lines,
                "comment_lines": self.comment_lines, "blank_lines": self.blank_lines,
                "fingerprints": list(self.fingerprints)}


class _Snapshot:
    __slots__ = ("raw", "bom", "rows", "keys", "inventory")

    def __init__(self, raw: bytes) -> None:
        if len(raw) > MAX_FILE_BYTES:
            raise KeyFileFormatError("The key file exceeds the size limit.")
        self.raw = raw
        self.bom = b""
        encoding = "utf-8"
        for bom, candidate in ((b"\xef\xbb\xbf", "utf-8"),
                               (b"\xff\xfe", "utf-16-le"),
                               (b"\xfe\xff", "utf-16-be")):
            if raw.startswith(bom):
                self.bom, encoding = bom, candidate
                raw = raw[len(bom):]
                break
        try:
            text = raw.decode(encoding)
        except UnicodeError:
            raise KeyFileFormatError("The key file encoding is invalid.") from None
        self.rows: list[tuple[bytes, KeyRef | None]] = []
        self.keys: list[KeyRef] = []
        seen: set[str] = set()
        key_lines = comments = blanks = 0
        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            key = None
            if not stripped:
                blanks += 1
            elif stripped.startswith(("#", ";", "//")):
                comments += 1
            else:
                key = KeyRef(stripped)
                key_lines += 1
                # Equality is checked with the full credential, not a truncated
                # fingerprint, so a digest collision cannot alter deduplication.
                if stripped not in seen:
                    seen.add(stripped)
                    self.keys.append(key)
            self.rows.append((line.encode(encoding), key))
        self.inventory = Inventory(key_lines, len(self.keys), key_lines - len(self.keys),
                                   comments, blanks,
                                   tuple(key.fingerprint for key in self.keys))

    def without(self, key: KeyRef) -> tuple[bytes, int]:
        value = key.authentication_value()
        kept = []
        removed = 0
        for raw, candidate in self.rows:
            if candidate is not None and candidate.authentication_value() == value:
                removed += 1
            else:
                kept.append(raw)
        return self.bom + b"".join(kept), removed

    def __repr__(self) -> str:
        return f"_Snapshot(inventory={self.inventory!r})"


def _amount(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise BalanceCheckError("The wallet returned an invalid amount.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise BalanceCheckError("The wallet returned an invalid amount.") from None
    if not amount.is_finite() or amount < 0:
        raise BalanceCheckError("The wallet returned an invalid amount.")
    return amount


@dataclass(frozen=True, init=False, repr=False)
class VerifiedBalance:
    """Parsed successful wallet GET; contains no bearer key or raw response.

    The HTTP adapter must call ``from_response`` only for the response obtained
    by authenticating that exact KeyRef to the indicated endpoint. Root clients
    may reuse their existing transport without giving this helper a POST path.
    """
    __slots__ = ("fingerprint", "balance", "frozen", "endpoint", "observed_at")
    fingerprint: str
    balance: Decimal
    frozen: Decimal
    endpoint: str
    observed_at: float

    def __init__(self):
        raise TypeError("Use VerifiedBalance.from_response for a successful wallet GET.")

    @classmethod
    def from_response(cls, key: KeyRef, *, http_status: int,
                      body: Mapping, endpoint: str,
                      observed_at: float | None = None) -> "VerifiedBalance":
        if endpoint not in BALANCE_ENDPOINTS.values():
            raise BalanceCheckError("The response is not from an allowed wallet endpoint.")
        if isinstance(http_status, bool) or http_status != 200:
            status = http_status if type(http_status) is int else None
            raise BalanceCheckError("The wallet request did not succeed.", http_status=status)
        if not isinstance(body, Mapping):
            raise BalanceCheckError("The wallet returned an invalid response shape.")
        code = body.get("code")
        if type(code) is not int or code != 0:
            raise BalanceCheckError("The wallet API rejected the request.",
                                    http_status=http_status,
                                    api_code=code if type(code) is int else None)
        data = body.get("data")
        if not isinstance(data, Mapping):
            raise BalanceCheckError("The wallet returned an invalid data shape.")
        result = object.__new__(cls)
        object.__setattr__(result, "fingerprint", key.fingerprint)
        object.__setattr__(result, "balance", _amount(data.get("balance")))
        object.__setattr__(result, "frozen", _amount(data.get("frozen")))
        object.__setattr__(result, "endpoint", endpoint)
        stamp = time.monotonic() if observed_at is None else observed_at
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
            raise BalanceCheckError("The wallet observation time is invalid.")
        object.__setattr__(result, "observed_at", float(stamp))
        return result

    def require_empty(self, key: KeyRef, *, now: float | None = None) -> None:
        age = (time.monotonic() if now is None else now) - self.observed_at
        if self.fingerprint != key.fingerprint:
            raise KeyringError("The wallet proof belongs to a different key.")
        if not math.isfinite(age) or age < 0 or age > MAX_PROOF_AGE_SECONDS:
            raise KeyringError("The wallet proof is stale; refresh the balance before deletion.")
        if self.balance != 0 or self.frozen != 0:
            raise KeyringError("Only zero available and zero frozen credits permit deletion.")

    def summary(self) -> dict:
        return {"verified": True, "fingerprint": self.fingerprint,
                "balance": str(self.balance), "frozen": str(self.frozen),
                "endpoint": self.endpoint,
                "empty": self.balance == 0 and self.frozen == 0}

    def __repr__(self) -> str:
        return f"VerifiedBalance({self.summary()!r})"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BalanceCheckError("The wallet returned an unexpected redirect.")


def fetch_balance(key: KeyRef, *, version: str = "v3", timeout: float = 30.0) -> VerifiedBalance:
    """One read-only official wallet GET; no retries and no vendor error text."""
    endpoint = BALANCE_ENDPOINTS.get(version)
    if endpoint is None:
        raise BalanceCheckError("The wallet API version is unsupported.")
    request = Request(endpoint, headers={"Authorization": "Bearer " + key.authentication_value(),
                                        "Accept": "application/json"}, method="GET")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            status = response.status
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        # A numeric API code can help distinguish credit/task-slot errors. Never
        # retain or report the vendor's message, suggestion, body or auth header.
        api_code = None
        try:
            parsed = json.loads(error.read(MAX_RESPONSE_BYTES + 1))
            if isinstance(parsed, dict) and type(parsed.get("code")) is int:
                api_code = parsed["code"]
        except (ValueError, UnicodeError, OSError):
            pass
        status = error.code
        error.close()
        raise BalanceCheckError("The wallet request did not succeed.",
                                http_status=status, api_code=api_code) from None
    except (URLError, TimeoutError, OSError, ValueError, UnicodeError):
        raise BalanceCheckError("The wallet request failed or timed out.") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise BalanceCheckError("The wallet returned an oversized response.")
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeError):
        raise BalanceCheckError("The wallet returned invalid JSON.") from None
    return VerifiedBalance.from_response(key, http_status=status, body=body, endpoint=endpoint)


@contextmanager
def _exclusive_file(path: Path) -> Iterator[BinaryIO]:
    """Open the existing file without creating, replacing or sharing it."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        import msvcrt
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        handle = create(str(path), 0x80000000 | 0x40000000, 0, None, 3, 0x80, None)
        if handle == wintypes.HANDLE(-1).value:
            code = ctypes.get_last_error()
            if code in (32, 33):
                raise KeyFileBusy("The key file is in use; retry after the writer finishes.")
            raise KeyringError("The existing key file could not be opened exclusively.")
        try:
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
        except OSError:
            close(handle)
            raise KeyringError("The exclusive key file handle could not be acquired.") from None
        try:
            stream = os.fdopen(descriptor, "r+b", buffering=0)
        except OSError:
            os.close(descriptor)
            raise KeyringError("The exclusive key file stream could not be acquired.") from None
        with stream:
            yield stream
    else:
        import fcntl
        try:
            stream = path.open("r+b", buffering=0)
        except OSError:
            raise KeyringError("The existing key file could not be opened exclusively.") from None
        with stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise KeyFileBusy("The key file is in use; retry after the writer finishes.") from None
            try:
                yield stream
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def _write_all(stream: BinaryIO, value: bytes) -> None:
    stream.seek(0)
    remaining = memoryview(value)
    while remaining:
        count = stream.write(remaining)
        if count is None or count <= 0:
            raise OSError("Key file write did not progress.")
        remaining = remaining[count:]
    stream.truncate(len(value))
    stream.flush()
    os.fsync(stream.fileno())


@dataclass(frozen=True)
class RemovalResult:
    fingerprint: str
    removed_lines: int
    inventory: Inventory

    def summary(self) -> dict:
        return {"fingerprint": self.fingerprint, "removed_lines": self.removed_lines,
                "inventory": self.inventory.summary()}


class Keyring:
    def __init__(self, path: str | os.PathLike, *, lock_attempts: int = 12,
                 retry_delay: float = 0.1,
                 exclusive_opener: Callable = _exclusive_file) -> None:
        if type(lock_attempts) is not int or lock_attempts < 1:
            raise ValueError("lock_attempts must be a positive integer.")
        if not math.isfinite(retry_delay) or not 0 <= retry_delay <= 10:
            raise ValueError("retry_delay must be finite and between zero and ten seconds.")
        self.path = Path(path).absolute()
        self.lock_attempts = lock_attempts
        self.retry_delay = retry_delay
        self._opener = exclusive_opener

    def __repr__(self) -> str:
        return "Keyring(credentials=<private file>)"

    def _read(self) -> _Snapshot:
        for attempt in range(self.lock_attempts):
            try:
                with self.path.open("rb") as stream:
                    return _Snapshot(stream.read(MAX_FILE_BYTES + 1))
            except PermissionError:
                if attempt + 1 == self.lock_attempts:
                    raise KeyFileBusy("The key file is in use; refresh could not finish.") from None
                time.sleep(self.retry_delay)
            except OSError:
                raise KeyringError("The key file could not be read.") from None
        raise AssertionError("Unreachable key file read state.")

    def inventory(self) -> Inventory:
        return self._read().inventory

    def keys(self) -> tuple[KeyRef, ...]:
        """Fresh deduplicated credentials for a secret-safe client, in file order."""
        return tuple(self._read().keys)

    def select(self, *, after: KeyRef | None = None,
               exclude_fingerprints: frozenset[str] = frozenset()) -> KeyRef | None:
        """Refresh before every selection; exclusions never delete credentials."""
        keys = self._read().keys
        start = 0
        if after is not None:
            for index, key in enumerate(keys):
                if key.authentication_value() == after.authentication_value():
                    start = index + 1
                    break
        for key in keys[start:] + keys[:start]:
            if key.fingerprint not in exclude_fingerprints:
                return key
        return None

    def remove_confirmed_empty(self, key: KeyRef, proof: VerifiedBalance) -> RemovalResult:
        """Remove every exact occurrence of only the verified-empty credential.

        Retry acquisition rather than using an old snapshot. Revalidate proof
        freshness *inside* the acquired transaction before any mutation.
        """
        if not isinstance(key, KeyRef) or not isinstance(proof, VerifiedBalance):
            raise KeyringError("A verified wallet proof is required before deletion.")
        proof.require_empty(key)
        for attempt in range(self.lock_attempts):
            try:
                with self._opener(self.path) as stream:
                    proof.require_empty(key)
                    stream.seek(0)
                    original = stream.read(MAX_FILE_BYTES + 1)
                    snapshot = _Snapshot(original)
                    replacement, removed = snapshot.without(key)
                    if removed:
                        try:
                            _write_all(stream, replacement)
                        except Exception:
                            try:
                                _write_all(stream, original)
                            except Exception:
                                raise KeyringError("Key file write and rollback failed; stop all key mutations.") from None
                            raise KeyringError("Key file update failed; original bytes were restored.") from None
                    return RemovalResult(key.fingerprint, removed,
                                         _Snapshot(replacement).inventory)
            except KeyFileBusy:
                if attempt + 1 == self.lock_attempts:
                    raise KeyFileBusy("The key file remained in use; no key was removed.") from None
                time.sleep(self.retry_delay)
        raise AssertionError("Unreachable key file removal state.")

    def rotate_confirmed_empty(self, key: KeyRef, proof: VerifiedBalance, *,
                               exclude_fingerprints: frozenset[str] = frozenset()) -> KeyRef | None:
        self.remove_confirmed_empty(key, proof)
        # Mandatory second fresh read includes newly appended credentials and
        # avoids retaining the exclusive transaction's previous inventory.
        return self.select(exclude_fingerprints=exclude_fingerprints)
