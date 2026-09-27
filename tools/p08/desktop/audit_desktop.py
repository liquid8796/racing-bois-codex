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
from pathlib import Path, PurePosixPath
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


UNITY_DEPENDENCY_ROOTS = ["Assets/RacingBois/Scenes/Race.unity", "Assets/RacingBois/Settings/Desktop/DesktopPipeline.asset"]
BUILT_IN_DEPENDENCIES = {"Resources/unity_builtin_extra", "Library/unity default resources"}


def canonical_source_path(relative: str) -> None:
    if (not isinstance(relative, str) or not relative or any(c in relative for c in "\\:%\x00")
            or relative != relative.strip() or PurePosixPath(relative).is_absolute()
            or any(part in {"", ".", ".."} or part != part.strip() or part.endswith(".") for part in relative.split("/"))):
        raise ValueError("Build source path is not canonical and project relative")


def checked_source_file(relative: str) -> Path:
    canonical_source_path(relative)
    candidate = PROJECT / relative
    for part in [candidate, *candidate.parents]:
        if part == PROJECT:
            break
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise ValueError("Build source path traverses a symlink or junction")
    path = DISTRIBUTION.inside(candidate, PROJECT)
    if not path.is_file():
        raise ValueError("Build source file is missing")
    return path


def checked_file_row(row: dict) -> dict:
    if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"}:
        raise ValueError("Build file row is invalid")
    canonical_source_path(row["path"])
    if type(row["bytes"]) is not int or row["bytes"] < 0 or not isinstance(row["sha256"], str) or not HEX.fullmatch(row["sha256"]):
        raise ValueError("Build file fingerprint is invalid")
    path = checked_source_file(row["path"])
    if path.stat().st_size != row["bytes"] or DISTRIBUTION.digest(path) != row["sha256"]:
        raise ValueError("Current source differs from the actual Unity build")
    return row


def dependency_fingerprint(receipt: dict) -> str:
    lines = ["unity " + receipt["unityVersion"]] + ["root " + path for path in receipt["unityDependencyRoots"]]
    lines += ["asset " + row["assetPath"] + " " + row["path"] + " " + row["sha256"] for row in receipt["unityDependencies"]]
    lines += ["package " + row["name"] + " " + row["version"] + " " + row["resolvedPath"] + " " + row["manifest"]["sha256"] for row in receipt["unityPackages"]]
    lines += ["builtin " + path for path in receipt["unityBuiltInDependencies"]]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def audit_dependency_manifest(receipt: dict) -> dict:
    """Check the selected engine closure; this does not authenticate arbitrary JSON.

    PackageCache is admitted only through each exact resolved package directory
    and logical suffix. Explicit built-ins are bound to the Unity version.
    """
    if type(receipt.get("unityDependencySchema")) is not int or receipt["unityDependencySchema"] != 2 or receipt.get("unityDependencyRoots") != UNITY_DEPENDENCY_ROOTS:
        raise ValueError("Engine dependency roots/schema are missing or differ")
    if not isinstance(receipt.get("unityVersion"), str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+[abfp][0-9]+", receipt["unityVersion"]):
        raise ValueError("Unity version binding is missing")
    packages, built_ins, rows = receipt.get("unityPackages"), receipt.get("unityBuiltInDependencies"), receipt.get("unityDependencies")
    if not isinstance(packages, list) or not isinstance(built_ins, list) or not isinstance(rows, list) or not rows:
        raise ValueError("Engine dependency closure is absent")
    if any(not isinstance(p, str) for p in built_ins) or built_ins != sorted(set(built_ins)) or set(built_ins) - BUILT_IN_DEPENDENCIES:
        raise ValueError("Unknown or duplicate built-in dependency")
    result, by_package, logical_seen, physical_seen = {}, {}, set(), set()
    lock = json.loads(checked_source_file("Packages/packages-lock.json").read_text(encoding="utf-8-sig"))["dependencies"]
    for package in packages:
        if not isinstance(package, dict) or set(package) != {"name", "version", "resolvedPath", "manifest"}:
            raise ValueError("Resolved package record is invalid")
        name, version, resolved = package["name"], package["version"], package["resolvedPath"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]+", name) or name in by_package or not isinstance(version, str) or not version:
            raise ValueError("Resolved package identity is invalid or duplicated")
        canonical_source_path(resolved)
        prefix = "Library/PackageCache/" + name + "@"
        if resolved != "Packages/" + name and not (resolved.startswith(prefix) and len(resolved) > len(prefix) and "/" not in resolved[len(prefix):]):
            raise ValueError("Resolved package is outside its exact embedded/cache directory")
        manifest = checked_file_row(package["manifest"])
        if manifest["path"] != resolved + "/package.json":
            raise ValueError("Resolved package manifest path differs")
        metadata = json.loads((PROJECT / manifest["path"]).read_text(encoding="utf-8-sig"))
        if metadata.get("name") != name or metadata.get("version") != version or name not in lock:
            raise ValueError("Resolved package identity is not bound to its manifest/lock")
        if lock[name].get("source") == "registry" and lock[name].get("version") != version:
            raise ValueError("Resolved registry package version differs from package lock")
        by_package[name] = package; result[manifest["path"]] = manifest
    if list(by_package) != sorted(by_package):
        raise ValueError("Resolved package order differs")
    used_packages = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"assetPath", "path", "sha256", "bytes"}:
            raise ValueError("Engine dependency row is invalid")
        logical = row["assetPath"]; canonical_source_path(logical)
        if logical.casefold() in logical_seen or not isinstance(row["path"], str) or row["path"].casefold() in physical_seen:
            raise ValueError("Engine dependency path is duplicated")
        logical_seen.add(logical.casefold()); physical_seen.add(row["path"].casefold())
        if logical.startswith("Assets/"):
            expected = logical
        elif logical.startswith("Packages/") and len(logical.split("/")) >= 3:
            name = logical.split("/")[1]
            if name not in by_package:
                raise ValueError("Virtual package dependency is unresolved")
            used_packages.add(name)
            expected = by_package[name]["resolvedPath"] + "/" + logical.split("/", 2)[2]
        else:
            raise ValueError("Engine dependency is outside Unity logical roots")
        if row["path"] != expected:
            raise ValueError("Logical/physical dependency mapping differs")
        file = checked_file_row({k: row[k] for k in ["path", "sha256", "bytes"]}); result[file["path"]] = file
    logical_paths = [row["assetPath"] for row in rows]
    if logical_paths != sorted(logical_paths) or any(root not in logical_paths for root in UNITY_DEPENDENCY_ROOTS):
        raise ValueError("Engine dependency closure order or required roots differ")
    if used_packages != set(by_package):
        raise ValueError("Unused package record is outside the engine closure")
    if dependency_fingerprint(receipt) != receipt.get("unityDependencyFingerprint"):
        raise ValueError("Engine dependency aggregate differs from its bound files")
    return result


def audit_sources(receipt: dict) -> None:
    dependencies = audit_dependency_manifest(receipt)
    rows = receipt.get("sourceFiles")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Build source snapshot is absent")
    sources, seen, lines = {}, set(), []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"}:
            raise ValueError("Build source file row is invalid")
        relative = row["path"]; canonical_source_path(relative)
        if relative.casefold() in seen:
            raise ValueError("Build source path is duplicated")
        seen.add(relative.casefold()); sources[relative] = checked_file_row(row)
        lines.append(relative + " " + row["sha256"])
    if list(sources) != sorted(sources):
        raise ValueError("Build source snapshot order differs")
    authored = {p.relative_to(PROJECT).as_posix() for p in (PROJECT / "Assets/RacingBois").rglob("*") if p.is_file() and p.suffix in {".cs", ".uxml", ".uss"}}
    authored |= {p.relative_to(PROJECT).as_posix() for p in (PROJECT / "Packages/com.racingbois.foundation").rglob("*.cs") if p.is_file()}
    if set(sources) != authored | SOURCE_SETTINGS | set(dependencies):
        raise ValueError("Source snapshot does not equal the authored/settings/engine dependency union")
    if any(sources.get(path) != row for path, row in dependencies.items()):
        raise ValueError("Engine dependency closure differs in the source snapshot")
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
