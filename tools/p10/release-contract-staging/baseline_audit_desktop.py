"""Audit a Windows P08 installation without launching it or reading player saves.

The receipt binds distribution bytes to the actual Unity build. It does not
substitute for native graphics, input, audio, LAN/WAN or performance acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import struct
from pathlib import Path
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parents[3]
BUILD = PROJECT / "Build"
SPEC = importlib.util.spec_from_file_location("p08_distribution_audit", PROJECT / "tools/p08/content-pack/audit_publish.py")
assert SPEC is not None and SPEC.loader is not None
DISTRIBUTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISTRIBUTION)
HEX = re.compile(r"[a-f0-9]{64}\Z")
CONFIG_KEYS = {"schema", "connectionMode", "backendWebSocketUrl", "contentBaseUrl"}
FORBIDDEN_SUFFIXES = {".blend", ".blend1", ".blend2", ".wav", ".mp4", ".sqlite", ".sqlite3", ".db", ".pfx", ".key", ".pem", ".log"}
SOURCE_SETTINGS = {"ProjectSettings/ProjectSettings.asset", "ProjectSettings/GraphicsSettings.asset", "ProjectSettings/QualitySettings.asset", "ProjectSettings/EditorBuildSettings.asset", "Packages/manifest.json", "Packages/packages-lock.json", "Assets/RacingBois/Scenes/Race.unity"}


def validate_config(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 8192:
        raise ValueError("Public runtime config missing or oversized")
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS or type(config["schema"]) is not int or config["schema"] != 1 or config["connectionMode"] not in {"lan", "online"}:
        raise ValueError("Public runtime config identity or fields invalid")
    if not isinstance(config["backendWebSocketUrl"], str):
        raise ValueError("Public backend endpoint must be a string")
    value = config["backendWebSocketUrl"] or "ws://127.0.0.1:7777/multiplayer"
    endpoint = urlsplit(value)
    if not isinstance(value, str) or value != value.strip() or endpoint.scheme not in {"ws", "wss"} or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment or endpoint.path != "/multiplayer":
        raise ValueError("Public backend endpoint invalid")
    if config["connectionMode"] == "online" and (endpoint.scheme != "wss" or not config["backendWebSocketUrl"]):
        raise ValueError("Online requires an explicit trusted WSS endpoint")
    content = config["contentBaseUrl"]
    if not isinstance(content, str):
        raise ValueError("Public content endpoint must be a string")
    if content:
        origin = urlsplit(content)
        if content != content.strip() or "%" in content or "\\" in content or origin.scheme != "https" or not origin.hostname or origin.username or origin.password or origin.query or origin.fragment:
            raise ValueError("Remote content endpoint must be public HTTPS")
    return {"schema": 1, "connectionMode": config["connectionMode"], "backendEndpoint": value, "contentSource": "installed" if not content else "https"}


def audit_pack(root: Path, expected_hash: str, exact_files: bool = True) -> tuple[dict, list[dict]]:
    manifest, rows = DISTRIBUTION.audit(root, expected_hash)
    if manifest.get("buildTarget") != "StandaloneWindows64":
        raise ValueError("Desktop rejects content bundles from another platform")
    for entry in manifest["bundles"]:
        if entry["kind"] != "music" and (type(entry.get("crc")) is not int or not 0 <= entry["crc"] <= 0xFFFFFFFF):
            raise ValueError("Unity bundle CRC missing or invalid")
    expected = {row["url"] for row in rows} | {"manifest.json"}
    if exact_files:
        actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and not path.name.endswith(".meta")}
        if actual != expected:
            raise ValueError("Installed content contains missing or unregistered files")
    manifest_path = root / "manifest.json"
    rows.append({"id": "manifest", "kind": "manifest", "url": "manifest.json", "bytes": manifest_path.stat().st_size, "sha256": DISTRIBUTION.digest(manifest_path)})
    return manifest, rows


def pe_machine(path: Path) -> str:
    with path.open("rb") as stream:
        if path.stat().st_size < 64:
            raise ValueError("Windows PE header is truncated")
        if stream.read(2) != b"MZ":
            raise ValueError("Windows player is not a PE binary")
        stream.seek(0x3C)
        pointer = struct.unpack("<I", stream.read(4))[0]
        if pointer < 0x40 or pointer + 26 > path.stat().st_size:
            raise ValueError("Windows PE header is truncated")
        stream.seek(pointer)
        if stream.read(4) != b"PE\0\0" or struct.unpack("<H", stream.read(2))[0] != 0x8664:
            raise ValueError("Windows player is not x64")
        stream.seek(pointer + 24)
        if struct.unpack("<H", stream.read(2))[0] != 0x20B:
            raise ValueError("Windows player is not PE32+")
    return "AMD64 / PE32+"


def audit_sources(receipt: dict) -> None:
    rows = receipt.get("sourceFiles")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Build source snapshot is absent")
    seen = set()
    lines = []
    for row in rows:
        relative = row.get("path", "")
        if not relative or ".." in relative or "\\" in relative or relative in seen:
            raise ValueError("Build source snapshot path is invalid or duplicated")
        code = relative.startswith(("Assets/RacingBois/", "Packages/com.racingbois.foundation/")) and Path(relative).suffix in {".cs", ".uxml", ".uss"}
        verifier = relative.startswith("tools/p08/desktop/") and Path(relative).suffix == ".py"
        if relative not in SOURCE_SETTINGS and not code and not verifier:
            raise ValueError("Build source snapshot is outside the explicit code/settings allowlist")
        seen.add(relative)
        path = DISTRIBUTION.inside(PROJECT / relative, PROJECT)
        if path.stat().st_size != row.get("bytes") or DISTRIBUTION.digest(path) != row.get("sha256"):
            raise ValueError("Current source differs from the actual Unity build")
        lines.append(relative + " " + row["sha256"])
    if hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest() != receipt.get("sourceFingerprint"):
        raise ValueError("Build source aggregate differs from its declared files")


def audit_player(root: Path, build_receipt: Path, expected_hash: str, verify_source: bool = True) -> dict:
    if root.is_symlink() or any(path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()) for path in root.rglob("*")):
        raise ValueError("Installation must not contain symlinks or junctions")
    receipt = json.loads(build_receipt.read_text(encoding="utf-8-sig"))
    if receipt.get("schema") != 1 or receipt.get("passed") is not True or receipt.get("sourceBindingPassed") is not True or receipt.get("result") != "Succeeded" or receipt.get("target") != "StandaloneWindows64" or receipt.get("scriptingBackend") != "Mono2x" or receipt.get("contentHash") != expected_hash or not HEX.fullmatch(receipt.get("sourceFingerprint", "")):
        raise ValueError("Actual Unity release receipt is absent or mismatched")
    if receipt.get("errors") != 0:
        raise ValueError("Unity reported player build errors")
    output = receipt.get("output", "")
    if not output or (PROJECT / output).resolve() != root.resolve():
        raise ValueError("Player root differs from the actual build receipt")
    if verify_source:
        audit_sources(receipt)
    executable_machine = pe_machine(root / "RacingBois.exe")
    pe_machine(root / "UnityPlayer.dll")
    managed = root / "RacingBois_Data/Managed/RacingBois.Client.Bootstrap.dll"
    if not managed.is_file() or not (root / "MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll").is_file():
        raise ValueError("Selected Mono bootstrap/runtime is missing")
    installed = root / "RacingBois_Data/StreamingAssets"
    manifest, content = audit_pack(installed / "Content", expected_hash)
    if DISTRIBUTION.digest(installed / "Content/manifest.json") != receipt.get("manifestSha256"):
        raise ValueError("Installed manifest differs from the Unity build")
    config = validate_config(installed / "RacingBois.runtime.json")
    if config["contentSource"] != "installed":
        raise ValueError("This offline-ready release must resolve installed content")
    actual = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name == ".env" or path.name.startswith(".env."):
            raise ValueError("Source master, research, private data or diagnostic file included")
        actual.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": DISTRIBUTION.digest(path)})
    if {row["path"]: (row["bytes"], row["sha256"]) for row in actual} != {row["path"]: (row["bytes"], row["sha256"]) for row in receipt.get("playerFiles", [])}:
        raise ValueError("Player files differ from the actual Unity build receipt")
    expected_streaming = {"Content/" + row["url"] for row in content} | {"RacingBois.runtime.json"}
    actual_streaming = {path.relative_to(installed).as_posix() for path in installed.rglob("*") if path.is_file()}
    if actual_streaming != expected_streaming:
        raise ValueError("StreamingAssets includes an unregistered distribution file")
    return {"schema": 1, "passed": True, "target": "StandaloneWindows64", "scriptingBackend": "Mono2x", "peMachine": executable_machine,
            "contentHash": manifest["contentHash"], "sourceFingerprint": receipt["sourceFingerprint"], "unityBuildReceiptSha256": DISTRIBUTION.digest(build_receipt),
            "manifestSha256": receipt["manifestSha256"], "runtimeConfig": config, "contentFiles": len(content), "musicFiles": 25,
            "files": len(actual), "totalBytes": sum(row["bytes"] for row in actual), "entries": actual,
            "sourceVerified": verify_source,
            "scope": "Distribution bytes, source snapshot and PE identity. Unity CRC is bound to the separate Unity build receipt; native launch/performance not inferred."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player-root", type=Path, default=BUILD / "Desktop-P08")
    parser.add_argument("--build-receipt", type=Path, default=PROJECT / "docs/p08/desktop/build.json")
    parser.add_argument("--expected-content-hash", required=True)
    parser.add_argument("--receipt", type=Path)
    options = parser.parse_args()
    root = DISTRIBUTION.inside(options.player_root, BUILD)
    result = audit_player(root, options.build_receipt, options.expected_content_hash)
    if options.receipt:
        options.receipt.parent.mkdir(parents=True, exist_ok=True)
        options.receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "entries"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
