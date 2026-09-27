"""Verify immutable P08 delivery files and copy them beside a Web build.

No project scanning, database access or server mutation is performed. Unity is
responsible for platform/CRC validation; this verifies the distribution bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[3]
BUILD = PROJECT / "Build"
IDENTIFIER = re.compile(r"[a-z0-9-]{1,64}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
LIMIT = 64 * 1024 * 1024


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(131072), b""):
            value.update(block)
    return value.hexdigest()


def inside(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if resolved == root.resolve() or not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Destination must be inside {root}")
    return resolved


def audit(source: Path, expected_hash: str | None = None) -> tuple[dict, list[dict]]:
    source = source.resolve()
    manifest_path = source / "manifest.json"
    if manifest_path.stat().st_size > 131072:
        raise ValueError("Manifest exceeds the runtime limit")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema") != 1 or manifest.get("actorsId") != "actors":
        raise ValueError("Manifest identity differs from the runtime contract")
    if expected_hash and manifest.get("contentHash") != expected_hash:
        raise ValueError("Manifest gameplay content hash differs from the build")
    entries = manifest.get("bundles", [])
    if len(entries) != 31:
        raise ValueError("Expected six Unity bundles and 25 streamed Ogg files")
    seen: set[str] = set()
    receipts = []
    for entry in entries:
        identity = entry.get("id", "")
        relative = entry.get("url", "")
        sha = entry.get("sha256", "")
        size = entry.get("bytes", 0)
        kind = entry.get("kind")
        if not IDENTIFIER.fullmatch(identity) or identity in seen:
            raise ValueError("Invalid or duplicate content ID")
        seen.add(identity)
        if not HEX.fullmatch(sha) or type(size) is not int or not 0 < size <= LIMIT:
            raise ValueError(f"Invalid fingerprint or size: {identity}")
        if any(char in relative for char in "%\\?#:") or ".." in relative:
            raise ValueError(f"Unsafe delivery URL: {identity}")
        parts = PurePosixPath(relative)
        if parts.is_absolute() or not relative or len(relative) > 180:
            raise ValueError(f"Unsafe delivery URL: {identity}")
        path = inside(source / relative, source)
        suffix = ".ogg" if kind == "music" else ".bundle"
        if kind not in {"music", "actors", "route"} or not relative.endswith(sha + suffix):
            raise ValueError(f"Delivery name lacks its exact fingerprint: {identity}")
        if path.stat().st_size != size or digest(path) != sha:
            raise ValueError(f"Distribution bytes differ: {identity}")
        if kind != "music" and not entry.get("asset", "").startswith("assets/"):
            raise ValueError(f"Unity asset path invalid: {identity}")
        if kind == "route" and identity != "route-" + str(entry.get("courseIndex")):
            raise ValueError(f"Route identity mismatch: {identity}")
        if kind == "music":
            with path.open("rb") as stream:
                if stream.read(4) != b"OggS":
                    raise ValueError(f"Invalid Ogg container: {identity}")
        receipts.append({"id": identity, "kind": kind, "url": relative, "bytes": size, "sha256": sha})
    by_id = {entry["id"]: entry for entry in entries}
    if by_id.get("actors", {}).get("kind") != "actors":
        raise ValueError("Actor bundle absent")
    if sum(row["kind"] == "music" for row in receipts) != 25:
        raise ValueError("Music catalog count mismatch")
    for course in range(5):
        if by_id.get(f"route-{course}", {}).get("kind") != "route":
            raise ValueError("Route bundle absent")
    return manifest, receipts


def publish(source: Path, web_root: Path, expected_hash: str | None) -> dict:
    web_root = inside(web_root, BUILD)
    if not (web_root / "index.html").is_file():
        raise ValueError("Destination must contain the actual Web build index.html")
    manifest, receipts = audit(source, expected_hash)
    destination = inside(web_root / "Content", web_root)
    destination.mkdir(parents=True, exist_ok=True)
    for relative in [row["url"] for row in receipts] + ["manifest.json"]:
        target = inside(destination / relative, destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".copying")
        shutil.copyfile(source / relative, temporary)
        temporary.replace(target)
    _, copied = audit(destination, manifest["contentHash"])
    return {"passed": True, "source": str(source.resolve()), "destination": str(destination),
            "contentHash": manifest["contentHash"], "files": len(copied) + 1,
            "totalBytes": sum(row["bytes"] for row in copied), "entries": copied,
            "scope": "Distribution bytes only; Unity runtime/CRC requires its separate receipt"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=BUILD / "Content")
    parser.add_argument("--expected-content-hash")
    parser.add_argument("--web-root", type=Path)
    parser.add_argument("--receipt", type=Path)
    options = parser.parse_args()
    if options.web_root:
        result = publish(options.source, options.web_root, options.expected_content_hash)
    else:
        manifest, entries = audit(options.source, options.expected_content_hash)
        result = {"passed": True, "source": str(options.source.resolve()),
                  "contentHash": manifest["contentHash"], "files": len(entries) + 1,
                  "totalBytes": sum(row["bytes"] for row in entries), "entries": entries}
    if options.receipt:
        options.receipt.parent.mkdir(parents=True, exist_ok=True)
        options.receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "entries"}))


if __name__ == "__main__":
    main()
