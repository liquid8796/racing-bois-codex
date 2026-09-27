"""Freeze an audited Windows player into an immutable, reproducible candidate ZIP.

This tool cannot grant release acceptance. It never changes content masks,
launches Unity, reads player saves or bundles an online/offline realm database.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
MANIFEST = "evidence/package-manifest.json"
BUILD_RECEIPT = "evidence/unity-build.json"
PLAYER_PREFIX = "RacingBois-Windows/"
HEX = re.compile(r"[a-f0-9]{64}\Z")
RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.I)
TOOL_PATHS = ["tools/p10/package_desktop_candidate.py", "tools/p08/desktop/audit_desktop.py",
              "tools/p08/content-pack/audit_publish.py"]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return stream_digest(stream)


def stream_digest(stream) -> str:
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        value.update(block)
    return value.hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def canonical_path(name: str) -> None:
    if (not isinstance(name, str) or not name or any(c in name for c in '\\:<>"|?*')
            or any(ord(c) < 32 for c in name)
            or any(part in {"", ".", ".."} or part != part.strip() or part.endswith(".")
                   or RESERVED.fullmatch(part) for part in name.split("/"))):
        raise ValueError("Archive path is not a portable Windows relative path")


def no_links(path: Path) -> None:
    for part in [path, *path.parents]:
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise ValueError("Candidate path traverses a symlink or junction")


def tree_rows(root: Path) -> list[dict]:
    no_links(root)
    if not root.is_dir():
        raise ValueError("Player directory is missing")
    rows, seen = [], set()
    for path in sorted(root.rglob("*")):
        no_links(path)
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("Player contains a non-regular filesystem entry")
        name = path.relative_to(root).as_posix()
        canonical_path(name)
        if name.casefold() in seen:
            raise ValueError("Player contains case-insensitive path collisions")
        seen.add(name.casefold())
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": digest(path)})
    return sorted(rows, key=lambda row: row["path"])


def zip_info(name: str) -> zipfile.ZipInfo:
    canonical_path(name)
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_STORED
    return info


def write_archive(archive: Path, root: Path, rows: list[dict], build: bytes, manifest: dict) -> None:
    """Low-level writer; the command always runs the production audit first."""
    if tree_rows(root) != rows:
        raise ValueError("Player changed before packaging")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as output:
        for row in rows:
            path = root / row["path"]
            info = zip_info(PLAYER_PREFIX + row["path"])
            info.file_size = row["bytes"]
            with path.open("rb") as source, output.open(info, "w", force_zip64=row["bytes"] >= 2**31) as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
        output.writestr(zip_info(BUILD_RECEIPT), build)
        output.writestr(zip_info(MANIFEST), json_bytes(manifest))
    if tree_rows(root) != rows:
        raise ValueError("Player changed during packaging; archive is unaccepted")


def verify_archive(archive: Path, expected_sha256: str) -> dict:
    """Verify bytes without extraction; the external digest is the trust anchor."""
    no_links(archive)
    if not isinstance(expected_sha256, str) or not HEX.fullmatch(expected_sha256) or digest(archive) != expected_sha256:
        raise ValueError("Archive differs from the selected external SHA256")
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(name.casefold() for name in names)):
            raise ValueError("Archive contains duplicate or case-colliding paths")
        for info in infos:
            canonical_path(info.filename)
            if (info.is_dir() or info.compress_type != zipfile.ZIP_STORED or info.flag_bits & 1
                    or info.date_time != (1980, 1, 1, 0, 0, 0) or info.create_system != 3
                    or info.external_attr != (stat.S_IFREG | 0o644) << 16 or info.comment):
                raise ValueError("Archive contains unexpected entry type or metadata")
        if source.comment or MANIFEST not in names or BUILD_RECEIPT not in names:
            raise ValueError("Archive evidence is missing or metadata differs")
        if source.getinfo(MANIFEST).file_size > 16 * 1024 * 1024 or source.getinfo(BUILD_RECEIPT).file_size > 16 * 1024 * 1024:
            raise ValueError("Archive evidence exceeds the size limit")
        manifest = json.loads(source.read(MANIFEST))
        required = {"schema", "kind", "releaseAccepted", "contentHash", "sourceFingerprint", "buildReceiptSha256", "packagingTools", "files"}
        if (not isinstance(manifest, dict) or set(manifest) != required or type(manifest["schema"]) is not int
                or manifest["schema"] != 1 or manifest["kind"] != "windows-player-candidate"
                or manifest["releaseAccepted"] is not False or not isinstance(manifest["contentHash"], str)
                or not manifest["contentHash"] or not HEX.fullmatch(manifest.get("sourceFingerprint", ""))
                or not HEX.fullmatch(manifest.get("buildReceiptSha256", ""))):
            raise ValueError("Archive candidate manifest is invalid")
        tool_rows = manifest["packagingTools"]
        if not isinstance(tool_rows, dict) or set(tool_rows) != set(TOOL_PATHS) or any(not isinstance(value, str) or not HEX.fullmatch(value) for value in tool_rows.values()):
            raise ValueError("Archive packaging tool bindings are invalid")
        rows = manifest["files"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("Archive player manifest is absent")
        declared = []
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}
                    or type(row["bytes"]) is not int or row["bytes"] < 0
                    or not isinstance(row["sha256"], str) or not HEX.fullmatch(row["sha256"])):
                raise ValueError("Archive player file record is invalid")
            canonical_path(row["path"])
            declared.append(PLAYER_PREFIX + row["path"])
        if declared != sorted(set(declared)) or names != declared + [BUILD_RECEIPT, MANIFEST]:
            raise ValueError("Archive file set/order differs from its exact manifest")
        for row, name in zip(rows, declared):
            if source.getinfo(name).file_size != row["bytes"]:
                raise ValueError("Archived player file size differs")
            with source.open(name) as stream:
                if stream_digest(stream) != row["sha256"]:
                    raise ValueError("Archived player file hash differs")
        raw_build = source.read(BUILD_RECEIPT)
        if hashlib.sha256(raw_build).hexdigest() != manifest["buildReceiptSha256"]:
            raise ValueError("Archived Unity receipt bytes differ")
        build = json.loads(raw_build)
        if (build.get("passed") is not True or build.get("sourceBindingPassed") is not True
                or build.get("result") != "Succeeded" or build.get("target") != "StandaloneWindows64"
                or build.get("scriptingBackend") != "Mono2x" or build.get("errors") != 0
                or build.get("contentHash") != manifest["contentHash"]
                or build.get("sourceFingerprint") != manifest["sourceFingerprint"]
                or sorted(build.get("playerFiles", []), key=lambda row: row["path"]) != rows):
            raise ValueError("Archived Unity receipt/player binding differs")
    return {"archiveSha256": expected_sha256, "bytes": archive.stat().st_size, "files": len(rows),
            "contentHash": manifest["contentHash"], "sourceFingerprint": manifest["sourceFingerprint"],
            "archiveIntegrityPassed": True, "releaseAccepted": False,
            "scope": "Exact candidate archive integrity against the selected external digest. Does not authenticate the original Unity receipt or accept visuals, gameplay, hardware, LAN or geography."}


def package_candidate(player: Path, build_receipt: Path, expected_hash: str, archive: Path) -> dict:
    # Validate caller paths before resolve, so a parent link cannot hide itself.
    for path in [player, build_receipt, archive]:
        no_links(path)
    player, build_receipt, archive = player.resolve(), build_receipt.resolve(), archive.resolve()
    if not player.is_relative_to(PROJECT / "Build") or not build_receipt.is_relative_to(PROJECT):
        raise ValueError("Select a project-owned build and its actual Unity receipt")
    if (not archive.is_relative_to(PROJECT / "Build/Packages") or archive.suffix != ".zip"
            or archive.is_relative_to(player)):
        raise ValueError("Archive must be a new ZIP under Build/Packages outside the player")
    receipt_path = archive.with_suffix(".candidate.json")
    if archive.exists() or receipt_path.exists():
        raise ValueError("Candidate archive or receipt already exists; never overwrite")
    tools_before = {name: digest(PROJECT / name) for name in TOOL_PATHS}
    raw_build = build_receipt.read_bytes()
    spec = importlib.util.spec_from_file_location("p10_desktop_audit", PROJECT / TOOL_PATHS[1])
    assert spec is not None and spec.loader is not None
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    verified = audit.audit_player(player, build_receipt, expected_hash, verify_source=True)
    rows = sorted(verified["entries"], key=lambda row: row["path"])
    manifest = {"schema": 1, "kind": "windows-player-candidate", "releaseAccepted": False,
                "contentHash": verified["contentHash"], "sourceFingerprint": verified["sourceFingerprint"],
                "buildReceiptSha256": hashlib.sha256(raw_build).hexdigest(), "packagingTools": tools_before,
                "files": rows}
    archive.parent.mkdir(parents=True, exist_ok=True)
    write_archive(archive, player, rows, raw_build, manifest)
    report = verify_archive(archive, digest(archive))
    audit.audit_player(player, build_receipt, expected_hash, verify_source=True)
    if raw_build != build_receipt.read_bytes() or tools_before != {name: digest(PROJECT / name) for name in TOOL_PATHS}:
        raise ValueError("Build receipt or packaging tools changed during packaging; archive is unaccepted")
    report.update({"schema": 1, "playerRoot": player.relative_to(PROJECT).as_posix(),
                   "archive": archive.relative_to(PROJECT).as_posix(), "buildReceipt": build_receipt.relative_to(PROJECT).as_posix(),
                   "buildReceiptSha256": manifest["buildReceiptSha256"], "sourceVerifiedBeforeAndAfter": True,
                   "packagingTools": tools_before, "lanHostIncluded": False,
                   "scope": "Audited Windows player candidate and exact archive bytes. No final release, visual, runtime, hardware, physical LAN or geographic acceptance."})
    with receipt_path.open("xb") as output:
        output.write(json_bytes(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    package = commands.add_parser("package")
    package.add_argument("--player-root", required=True, type=Path)
    package.add_argument("--build-receipt", required=True, type=Path)
    package.add_argument("--expected-content-hash", required=True)
    package.add_argument("--archive", required=True, type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("--archive", required=True, type=Path)
    verify.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    report = (package_candidate(args.player_root, args.build_receipt, args.expected_content_hash, args.archive)
              if args.command == "package" else verify_archive(args.archive, args.expected_sha256))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
