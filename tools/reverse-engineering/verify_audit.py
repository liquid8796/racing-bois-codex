"""Read-only source integrity and cross-artifact audit verification.

This validates the research evidence, not game parity or production readiness.
Run from any directory. Never executes the source game or changes its files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from datetime import datetime, timezone
from urllib.parse import unquote


PROJECT = pathlib.Path(__file__).resolve().parents[2]
EVIDENCE = PROJECT / "docs/reverse-engineering"


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path,
                        default=pathlib.Path(r"C:\Users\Liquid\Downloads\Unity\racing_bois_mod"))
    parser.add_argument("--video", type=pathlib.Path,
                        default=pathlib.Path(r"C:\Users\Liquid\Downloads\prompt\Road Rash PC (1995) - Big Game Mode (All Levels).mp4"))
    args = parser.parse_args()
    destination = EVIDENCE / "verification-summary.json"
    failures: list[str] = []
    checks: dict[str, object] = {}

    def check(ok: bool, label: str) -> None:
        if not ok:
            failures.append(label)

    assets = EVIDENCE / "assets"
    manifest = read_json(assets / "source_manifest.json")
    summary = read_json(assets / "summary.json")
    paths = [entry["path"] for entry in manifest]
    actual = {p.relative_to(args.source).as_posix() for p in args.source.rglob("*") if p.is_file()}
    check(actual == set(paths), "source path set differs from manifest")
    check(len(paths) == len(set(paths)) == summary["file_count"], "file count/duplicate path mismatch")
    check(sum(e["bytes"] for e in manifest) == summary["total_bytes"], "source byte total mismatch")
    check(len({e["sha256"] for e in manifest}) == summary["unique_hashes"], "unique hash count mismatch")
    for entry in manifest:
        path = args.source / entry["path"]
        check(path.is_file(), f"missing source: {entry['path']}")
        if path.is_file():
            check(path.stat().st_size == entry["bytes"], f"size changed: {entry['path']}")
            check(sha_file(path) == entry["sha256"], f"hash changed: {entry['path']}")
    checks["source_files_rehashed"] = len(manifest)
    checks["source_bytes"] = summary["total_bytes"]

    entries = read_json(assets / "resource_entries.json")
    check(len(entries) == summary["crsr_entries"], "CRSR entry count mismatch")
    archive_bytes = {path: (args.source / path).read_bytes() for path in {entry["path"] for entry in entries}}
    for entry in entries:
        data = archive_bytes[entry["path"]]
        start, size = entry["offset"], entry["size"]
        check(0 <= start <= start + size <= len(data), f"CRSR member out of bounds: {entry['path']}/{entry['index']}")
        check(hashlib.sha256(data[start:start + size]).hexdigest() == entry["sha256"],
              f"CRSR member hash mismatch: {entry['path']}/{entry['index']}")
    checks["crsr_member_hashes_verified"] = len(entries)

    families = read_json(assets / "families.json")
    check(len(families) == summary["family_entries"], "FAM count mismatch")
    for family in families:
        if family["compression"] == 1:
            check(family["crc32_expected"] == family["crc32_actual"], f"FAM CRC mismatch: {family['id']}")
    check(not summary["failures"], "asset audit recorded failures")
    internals = read_json(assets / "internals_summary.json")
    check(not internals["failures"], "internal parser recorded failures")
    check(internals["animations"] == internals["animations_validated"], "animation tables not all validated")
    mips = read_json(assets / "mip_summary.json")
    check(not mips["failures"], "mip structure parser recorded failures")
    checks["mip_structure_receipt"] = mips
    validation = read_json(assets / "validation.json")
    check(validation["avi_all_streams_fully_decoded"] == summary["video_files"], "AVI full decode report incomplete")
    check(validation["avi_video_chunks_match_header_frames"] == summary["video_reported_frames"],
          "AVI RIFF chunk/header frame count mismatch")
    check(validation["source_files_sha256_unchanged"] == len(manifest), "asset validation snapshot count mismatch")
    checks["asset_validation_receipt"] = validation

    logic = EVIDENCE / "logic"
    binary = (args.source / "RacingBois.exe").read_bytes()
    functions = read_json(logic / "function_index.json")
    for item in functions:
        start = int(item["file_offset_start"], 16)
        chunk = binary[start:start + item["length"]]
        check(len(chunk) == item["length"], f"short function slice: {item['analyst_label']}")
        check(hashlib.sha256(chunk).hexdigest() == item["sha256_code_slice"],
              f"function slice hash mismatch: {item['analyst_label']}")
    logic_receipt = read_json(logic / "verification.json")
    check(logic_receipt["status"] == "PASS", "logic validation failed")
    check(len(functions) == logic_receipt["function_slices_verified"], "logic slice count mismatch")
    check(hashlib.sha256(binary).hexdigest() == logic_receipt["source_sha256"], "logic source fingerprint mismatch")
    saves = read_json(logic / "saves_decoded.json")
    check(sum(bool(s["valid"]) for s in saves) == logic_receipt["saves_validated"], "validated save count mismatch")
    checks["logic_slice_hashes_verified"] = len(functions)
    checks["logic_validation_receipt"] = logic_receipt

    video_dir = EVIDENCE / "video"
    coverage = read_json(video_dir / "coverage.json")
    frames = []
    for group, expected in coverage["groups"].items():
        group_frames = read_json(video_dir / group / "frames.json")
        check(len(group_frames) == expected, f"video frame count mismatch: {group}")
        frames.extend(group_frames)
    check(len(frames) == coverage["frames_reviewed"], "total reference frame count mismatch")
    check(len({f["timestamp_seconds"] for f in frames}) == coverage["unique_timestamps"], "unique timestamp mismatch")
    for frame in frames:
        check(pathlib.Path(frame["path"]).is_file(), f"reference frame missing: {frame['path']}")
    check(sha_file(args.video) == coverage["source_sha256"], "reference video fingerprint mismatch")
    checks["reference_frames_present"] = len(frames)
    checks["reference_unique_timestamps"] = coverage["unique_timestamps"]
    checks["reference_video_rehashed"] = True

    required = ["REQUIREMENTS.md", "PHASE_PLAN.md", "TECHNICAL_ARCHITECTURE.md",
                "UI_UX_DIRECTION.md", "ENGINEERING_STANDARDS.md", "REVERSE_ENGINEERING_REPORT.md"]
    for name in required:
        check((PROJECT / "docs" / name).is_file(), f"required document missing: {name}")
    markdown_files = [PROJECT / "README.md", *sorted((PROJECT / "docs").rglob("*.md"))]
    local_links = 0
    for markdown in markdown_files:
        content = markdown.read_text(encoding="utf-8-sig")
        for match in re.finditer(r"\]\(([^)]+)\)", content):
            target = match.group(1).strip().strip("<>")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target) or target.startswith("#"):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            linked_path = (markdown.parent / target).resolve()
            # This receipt is generated at the end of the same successful check.
            check(linked_path == destination.resolve() or linked_path.exists(),
                  f"broken local link in {markdown.relative_to(PROJECT)}: {target}")
            local_links += 1
    checks["local_document_links_checked"] = local_links
    checks["unity_assets_file_count"] = sum(1 for p in (PROJECT / "Assets").rglob("*") if p.is_file())

    result = {"status": "FAIL" if failures else "PASS", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_read_only": True, "source_game_executed": False,
              "scope": "Research artifact integrity only; not complete logic recovery, gameplay parity or product readiness.",
              "checks": checks, "failures": failures}
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
