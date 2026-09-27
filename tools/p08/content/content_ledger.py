"""Build/check the P08 reference-to-production register without copying reference media.

The generated ledger distinguishes a verified semantic unit from a unique source
file or compound family. Structural validation never implies content acceptance.
Only explicitly reviewed mappings can close a row; filename guesses cannot.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/p08/content"
RESEARCH_INPUTS = {
    "manifest": "docs/reverse-engineering/assets/source_manifest.json",
    "media": "docs/reverse-engineering/assets/media_metadata.json",
    "families": "docs/p01/assets/content_reference_ledger.json",
    "courses": "docs/p01/assets/course_summary.json",
    "display": "docs/p01/assets/display_units.json",
    "economy": "docs/reverse-engineering/logic/economy_tables.json",
    "triggers": "docs/p01/assets/media/trigger_references.json",
    "fonts": "docs/reverse-engineering/assets/fonts.json",
}
INPUTS = {"baseline": "docs/p08/content/reference-baseline.json",
          "mappings": "docs/p08/content/production-mappings.json"}
STATES = {"pending", "partial", "implemented_pending_qa", "accepted"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_path(relative):
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("Use a repository-relative POSIX path: " + str(relative))
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()) or Path(relative).is_absolute():
        raise ValueError("Path outside repository: " + relative)
    return path


def receipt(relative):
    path = safe_path(relative)
    if not path.is_file():
        raise ValueError("Required file missing: " + relative)
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)}


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def unique_groups(records):
    result = defaultdict(list)
    for record in records:
        result[record["sha256"]].append(record)
    return sorted(result.values(), key=lambda group: group[0]["path"])


def media_stats(records, media):
    def seconds(record):
        return Decimal(media[record["path"]]["format"]["duration"])
    groups = unique_groups(records)
    return {
        "files": len(records), "unique_file_hashes": len(groups),
        "gross_seconds": str(sum((seconds(r) for r in records), Decimal(0))),
        "deduplicated_seconds": str(sum((seconds(g[0]) for g in groups), Decimal(0))),
        "duration_basis": "ffprobe format duration from decoded source audit; file duration is not narrative or composition count",
    }


def capture_reference():
    """Archive portable audit metadata only; never copy pixels, audio or binaries."""
    data = {key: read(path) for key, path in RESEARCH_INPUTS.items()}
    data["media"] = [{"path": r["path"], "format": {"duration": r["format"]["duration"]}}
                     for r in data["media"]]
    data["triggers"] = [{"path": r["path"], "trigger_status": r["trigger_status"],
                         "literal_reference_count": len(r["literal_references"])} for r in data["triggers"]]
    data["fonts"] = [{"path": r["path"], "glyph_count": r["glyph_count"]} for r in data["fonts"]]
    data["economy"] = {"bikes": data["economy"]["bikes"]}
    snapshot = {"schema": 1, "policy": "Metadata-only portable snapshot of local audit outputs. No source assets or decoded samples included.",
                "upstream_audits": [receipt(path) for path in RESEARCH_INPUTS.values()], "data": data}
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / INPUTS["baseline"]).write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def build():
    source = dict(read(INPUTS["baseline"])["data"])
    source["mappings"] = read(INPUTS["mappings"])
    manifest = source["manifest"]
    media = {row["path"]: row for row in source["media"]}
    originals = {row["path"]: row for row in manifest}
    triggers = {row["path"]: row for row in source["triggers"]}
    rows = []

    def add(identifier, category, label, paths, unit, semantic, gap, detail=None):
        paths = sorted(set(paths))
        unknown = set(paths) - originals.keys()
        if unknown:
            raise ValueError("Unknown original reference paths: " + str(unknown))
        rows.append({
            "id": identifier, "category": category, "label": label,
            "reference_unit": unit, "semantic_independence_verified": semantic,
            "reference_files": paths, "reference_detail": detail or {},
            "status": "pending", "replacement_ids": [], "dependencies": [],
            "build_packs": [], "mapping_evidence": [], "qa_evidence": [],
            "remaining_work": gap,
        })

    def paths(prefix, suffix=None):
        return [r["path"] for r in manifest if r["path"].startswith(prefix)
                and (suffix is None or r["path"].endswith(suffix))]

    course_meta = {r["course"]: r for r in source["courses"]}
    for course in source["display"]["course_menu_lengths"]:
        code = Path(course["course_source"]).stem
        add("course-" + code.lower(), "courses", course["display_name"],
            [course["course_source"], "DATA/CARS/" + code + ".CAR"], "course family", True,
            "Original route/biome replacement, all five level finish/length/difficulty variants, browser quality-tier QA.",
            {"course_code": code, "menu_lengths": course["levels"], "structural_audit": course_meta[code],
             "counting_rule": "One course family; five playable level variants do not count as five independent track models.",
             "length_limit": "Menu display values are verified; world meters and all branch trajectories are not thereby proven."})
    for bike in source["economy"]["bikes"]:
        index = bike["internal_index"]
        add(f"bike-sku-{index:02d}", "bikes", bike["name"], ["DATA/BIKESPEC.RSC"], "bike SKU", True,
            "Distinct readable original design, source, prefab, SKU-specific handling and showroom/showcase integration; QA all tiers.",
            {"catalog_index": index, "resource_SPEC_id": bike["resource_SPEC_id"], "reference_name_string_id": bike["string_id"],
             "reference_price": bike["price"], "art_filename_mapping": "Unproven: no SPEC-to-showroom filename equivalence inferred here.",
             "counting_rule": "SKU count is not independent mesh/rig count; shared chassis must be declared."})
    names = sorted({Path(p).stem.rsplit("-", 1)[0] for p in paths("IMAGES/CHARS/") if "-" in Path(p).stem})
    for name in names:
        add("portrait-" + name.lower(), "characters", name,
            [p for p in paths("IMAGES/CHARS/") if Path(p).stem.startswith(name + "-")],
            "portrait identity with three states", True,
            "Create original identity with N/H/F-equivalent expressive states; integrate selection/dialog/results. Additional runtime roster identities remain a separate reverse gap.",
            {"states": ["N", "H", "F"], "rig_count_inference": "No evidence that eight portraits imply eight independent original rigs."})
    for role, refs in [("rider", ["HIBOB", "LOBOB", "HISHADOW", "LOSHADOW"]),
                       ("police", ["LOCOP", "HISHADOC", "LOSHADOC"])]:
        add("animation-" + role, "animation", role + " action coverage",
            ["DATA/BIKERS/" + ref + ".DAT" for ref in refs] + ["DATA/GLOBAL.RSC"],
            "action set requiring state mapping", False,
            "Map source action, left/right, hit, fall/recovery and timing to authored clips. Sprite frames, shadow variants and viewing angles are not independent clips.")
    for item in ["fist", "kick", "club", "chain"]:
        add("equipment-" + item, "equipment", item, ["DATA/GLOBAL.RSC", "DATA/BIKERS/HIBOB.DAT"],
            "gameplay equipment/action role", True,
            "Verify original/new contact state coverage, attachment, visuals and sound. Fist/kick use the rider rig rather than separate mesh counts.")
    for role, refs in [
        ("traffic", paths("DATA/CARS/") + ["DATA/FAMILIES.RSC"]),
        ("pedestrians-and-animals", ["DATA/FAMILIES.RSC", "DATA/GLOBAL.RSC"]),
        ("police", ["DATA/BIKERS/LOCOP.DAT", "DATA/GLOBAL.RSC", "DATA/FAMILIES.RSC"]),
        ("scenery", ["DATA/FAMILIES.RSC"] + paths("DATA/COURSES/")),
    ]:
        add("world-" + role, "world_roles", role, refs, "functional content group; independent design count unresolved", False,
            "Group source atlas/runtime semantics and all required variations before claiming coverage. Existing production examples are partial; no count inferred from a FAM, filename, renderer or LOD.")
    add("render-source-dependencies", "render_support", "Source indexed palette and biker mip template",
        ["DATA/PALETTE.RAW", "DATA/BIKERS/TEMPLATE.MIP"], "rendering dependencies, not independent semantic assets", False,
        "Original PBR/URP surface and color pipeline replaces indexed rendering; document visual role equivalence. No source palette/mip bytes enter production.")
    for family in source["families"]:
        add("family-" + family["reference_id"][4:], "family_catalog", family["reference_id"], ["DATA/FAMILIES.RSC"],
            "compound family; independent content count unknown", False,
            "Review visible atlas components; assign actual traffic/pedestrian/animal/scenery/texture semantics and explicit many-to-many replacements. Never close solely from a source filename.",
            {"original_reference_id": family["reference_id"], "course_references": family["course_references"].split(";") if family["course_references"] else [],
             "authoring_name_hints": family["source_animation_names"].split(";") if family["source_animation_names"] else [],
             "research_atlas_pages": family["research_atlas_pages"].split(";"), "unit_note": family["unit_note"]})
    for role, refs in [("CITY", ["CITY", "LCITY"]), ("NAPA", ["NAPA", "LNAPA"]),
                       ("PCH", ["PCH", "LPCH"]), ("PENIN", ["PENIN", "LPENIN"]), ("SIERRA", ["SIERRA", "LSIERRA"])]:
        add("horizon-" + role.lower(), "horizons", role + " distant landscape",
            ["IMAGES/HORIZONS/" + name + ".BOB" for name in refs], "high/low pair; one content role", True,
            "Original biome-specific distant scenery/sky with silhouette, lighting and web tier QA.")
    for role in ["RAT", "SPORT", "SUPER"]:
        add("dashboard-" + role.lower(), "ui_dashboard", role + " dashboard", paths("IMAGES/BIKES/" + role, ".BOB"),
            "dashboard family, metric/imperial and high/low variants", True,
            "Document original UI replacement or intentional coherent shared HUD, preserving units and readable meter/state information.")
    for role, refs in [("clouds", ["BIGCLOUD", "LILCLOUD"]), ("meter", ["BIGMETER", "LILMETER"]), ("matte", ["MATTE"])]:
        add("presentation-" + role, "presentation", role, ["IMAGES/" + name + ".BOB" for name in refs],
            "presentation role with quality variants", role != "clouds",
            "Original sky/HUD/presentation replacement and runtime visual QA; cloud source dimensions remain a loader-verification gap.")
    # Each unique image file is tracked, but portraits and showroom renders cannot inflate
    # the independently counted character/bike groups above.
    image_records = [r for r in manifest if r["extension"] in [".RRI", ".BMP"] and (r["category"] == "IMAGES" or r["extension"] == ".BMP")]
    for group in unique_groups(image_records):
        first = group[0]["path"]
        add("image-" + slug(first), "image_catalog", first, [r["path"] for r in group],
            "unique source image file; role may overlap character/bike/UI entries", False,
            "Review composition and runtime purpose; map to original production UI/art/state. A UI button or shared mesh alone does not prove equivalent art/content.",
            {"filename_group_hint": "/".join(first.split("/")[:-1]), "event_mapping": "Filename grouping only; exact branch/state selection may be unproven."})
    for category, records in [
        ("audio_effect", [r for r in manifest if r["path"].startswith("AUDIO/EFFECTS/")]),
        ("music_pcm", [r for r in manifest if r["path"].startswith("AUDIO/MUSIC/") and r["extension"] in [".RRA", ".WAV"]]),
        ("music_mids", [r for r in manifest if r["path"].startswith("AUDIO/MUSIC/") and r["extension"] == ".MID"]),
        ("cinematic", [r for r in manifest if r["category"] == "VIDEO"]),
    ]:
        for group in unique_groups(records):
            first = group[0]["path"]
            detail = {"source_aliases": [r["path"] for r in group], "event_mapping": "Unknown until reference event branches and replacement integration are reviewed."}
            if first in media:
                detail["duration_seconds"] = media[first]["format"]["duration"]
            detail["literal_reference_status"] = triggers.get(first, {}).get("trigger_status", "NOT_IN_MEDIA_TRIGGER_AUDIT")
            if category == "cinematic":
                detail["filename_role_hint"] = first.split("/")[1] if len(first.split("/")) == 3 else re.sub(r"\d+$", "", Path(first).stem)
                detail["production_policy"] = "New direction, staging, animation, sound and integration. Gameplay QA capture or a still repeated over time is not a replacement cinematic."
            if category.startswith("music"):
                detail["composition_count"] = "Unresolved; arrangements and PCM/MIDS counterparts must not count twice."
            add(category + "-" + slug(first), category, first, [r["path"] for r in group],
                "unique source file, not a proven independent composition/event", False,
                "Author original replacement, preserve source project and review meaningful role/variation; validate playback/trigger/mix or cinematic staging/integration. No source samples, re-encoding, duplicated padding or melody reuse.", detail)
    sbk = [r["path"] for r in manifest if r["extension"] == ".SBK"]
    add("music-soundfont-dependencies", "music_support", "Six source SoundFont 1.0 banks", sbk,
        "soundbank dependency group", False,
        "Original production instrument/synthesis sources may replace the soundbank architecture. Do not count 32 sample records as 32 independent compositions.")
    fonts = source["fonts"]
    font_paths = [r["path"] for r in fonts] if isinstance(fonts, list) else []
    add("typography", "typography", "Four source fonts", font_paths, "typography system", True,
        "Use licensed original/third-party production typography; verify glyphs, contrast, fallback and language coverage. Source font binaries must not ship.")
    language_paths = [r["path"] for r in manifest if Path(r["path"]).name in ["ENU.DLL", "DEU.DLL", "ESP.DLL", "FRA.DLL", "ITA.DLL"]]
    add("localization", "localization", "Five language bundles", language_paths, "localization language coverage", True,
        "Original Racing Bois copy with reviewed EN/DE/ES/FR/IT language coverage or an explicit product-scope decision. Do not infer five-language support from one multilingual font.",
        {"bundle_count": 5, "string_records_gross": 6832, "english_records": 1364, "counting_rule": "String IDs/duplicate messages are not 6832 unique authored scenes."})

    production = []
    for authored in source["mappings"]["production_assets"]:
        asset = dict(authored)
        for field in ["production_paths", "authoring_paths", "concept_paths", "provenance_paths", "qa_paths"]:
            asset[field] = [receipt(path) for path in asset.get(field, [])]
        production.append(asset)
    known = {item["id"] for item in production}
    by_id = {row["id"]: row for row in rows}
    for mapping in source["mappings"]["row_mappings"]:
        allowed = {"id", "status", "replacement_ids", "dependencies", "build_packs", "mapping_evidence", "qa_evidence", "remaining_work", "mapping_note"}
        if set(mapping) - allowed:
            raise ValueError("Mapping cannot overwrite immutable reference fields: " + mapping["id"])
        if mapping["id"] not in by_id:
            raise ValueError("Unknown row mapping " + mapping["id"])
        if mapping["status"] not in STATES:
            raise ValueError("Unknown mapping status")
        if set(mapping["replacement_ids"]) - known:
            raise ValueError("Unknown production asset ID in " + mapping["id"])
        by_id[mapping["id"]].update(mapping)
        by_id[mapping["id"]]["mapping_evidence"] = [receipt(p) for p in mapping.get("mapping_evidence", [])]
        by_id[mapping["id"]]["qa_evidence"] = [receipt(p) for p in mapping.get("qa_evidence", [])]

    baseline = {
        "source_files": len(manifest), "source_bytes": sum(r["bytes"] for r in manifest),
        "source_unique_hashes": len({r["sha256"] for r in manifest}),
        "course_families": 5, "course_level_variants": 25, "bike_skus": 15,
        "portrait_identities": 8, "portrait_state_images": 24,
        "compound_nonempty_families": 163, "independent_family_semantics_count": None,
        "image_files": len(image_records), "image_unique_hashes": len(unique_groups(image_records)),
        "horizon_pairs": 5, "dashboard_families": 3, "source_fonts": 4, "language_bundles": 5,
        "music_mids_files": 11, "music_soundbanks": 6, "independent_music_compositions": None,
    }
    for title, selector in [
        ("sfx", lambda r: r["path"].startswith("AUDIO/EFFECTS/")),
        ("pcm_music", lambda r: r["path"].startswith("AUDIO/MUSIC/") and r["extension"] in [".RRA", ".WAV"]),
        ("cinematics", lambda r: r["category"] == "VIDEO"),
    ]:
        baseline[title] = media_stats([r for r in manifest if selector(r)], media)
    production_states = dict(sorted(Counter(r["status"] for r in rows).items()))
    return {
        "schema": 1, "name": "Racing Bois ContentParityLedger", "policy": {
            "reference_only": "Source hashes, metadata and research links only; no original media copied into Assets or Build.",
            "concept_before_3d": "Generated and viewed 2D concept precedes new 3D authoring. Exact image model must not be invented if the provider does not expose it.",
            "counting": "Never sum these heterogeneous rows into an independent asset total. LODs, mips, frames, duplicate hashes, arrangements and SKU/portrait views are not independent content.",
            "acceptance": "File existence/hash or a passing ledger check is not visual, functional or originality acceptance. Hash difference does not detect crop/recolor/re-encoding. Source review and real QA remain mandatory.",
        },
        "inputs": [receipt(path) for path in INPUTS.values()],
        "baseline": baseline, "reference_source_files": manifest,
        "production_assets": production, "entries": rows,
        "coverage": {"rows": len(rows), "state_counts": production_states,
                     "all_required_mappings_accepted": all(r["status"] == "accepted" for r in rows),
                     "semantic_count_gate": "OPEN: compound-family semantics and music composition equivalence unresolved",
                     "global_coverage_percentage": None},
    }


def inspect(ledger, scan=True):
    errors = []
    rows = ledger["entries"]
    if len({row["id"] for row in rows}) != len(rows):
        errors.append("Duplicate semantic row IDs")
    original_hashes = {r["sha256"] for r in ledger["reference_source_files"]}
    originals = {r["path"]: r for r in ledger["reference_source_files"]}
    production = {a["id"]: a for a in ledger["production_assets"]}
    if len(production) != len(ledger["production_assets"]):
        errors.append("Duplicate production asset IDs")
    verified_paths = set()
    for item in ledger["inputs"] + [r for a in production.values() for key in
              ["production_paths", "authoring_paths", "concept_paths", "provenance_paths", "qa_paths"] for r in a[key]]:
        path = safe_path(item["path"])
        if not path.is_file() or receipt(item["path"]) != item:
            errors.append("Missing/stale bound file: " + item["path"])
        verified_paths.add(item["path"])
    for asset in production.values():
        if not asset["production_paths"] or not asset["authoring_paths"] or not asset["provenance_paths"]:
            errors.append("Incomplete provenance for " + asset["id"])
        if asset.get("asset_kind") == "3d" and not asset["concept_paths"]:
            errors.append("Missing concept for " + asset["id"])
        if asset.get("qa_state") == "accepted" and not asset["qa_paths"]:
            errors.append("Accepted production asset lacks QA evidence: " + asset["id"])
        if not asset.get("build_pack"):
            errors.append("Missing build pack for " + asset["id"])
        for item in asset["production_paths"]:
            if not item["path"].startswith(("Assets/", "Packages/")):
                errors.append("Production output is outside Unity import/runtime roots: " + item["path"])
            if item["sha256"] in original_hashes:
                errors.append("Direct source byte copy: " + item["path"])
    for row in rows:
        if row["status"] not in STATES:
            errors.append("Invalid state: " + row["id"])
        if set(row["replacement_ids"]) - production.keys():
            errors.append("Missing production mapping: " + row["id"])
        if set(row["reference_files"]) - originals.keys():
            errors.append("Unknown original reference: " + row["id"])
        if set(row["dependencies"]) - (production.keys() | {r["id"] for r in rows}):
            errors.append("Unknown dependency: " + row["id"])
        if row["status"] == "accepted":
            if not all([row["replacement_ids"], row["mapping_evidence"], row["qa_evidence"], row["build_packs"]]):
                errors.append("Accepted row lacks integration/mapping/QA evidence: " + row["id"])
            if row.get("remaining_work"):
                errors.append("Accepted row still lists unfinished work: " + row["id"])
            for identity in row["replacement_ids"]:
                if production.get(identity, {}).get("qa_state") != "accepted":
                    errors.append("Accepted row references unaccepted production asset: " + row["id"])
        for bound in row["mapping_evidence"] + row["qa_evidence"]:
            if receipt(bound["path"]) != bound:
                errors.append("Stale row evidence: " + bound["path"])
    required_reference_paths = {r["path"] for r in originals.values()
                                if r["category"] in {"AUDIO", "DATA", "IMAGES", "VIDEO", "TEXT"}
                                or r["extension"] == ".BMP"}
    referenced_paths = {path for row in rows for path in row["reference_files"]}
    for missing in sorted(required_reference_paths - referenced_paths):
        errors.append("Source asset file absent from reference register: " + missing)
    baseline = ledger["baseline"]
    expected = {"courses": 5, "bikes": 15, "characters": 8, "family_catalog": 163,
                "audio_effect": 72, "music_pcm": 14, "music_mids": 11, "cinematic": 59, "horizons": 5}
    counts = Counter(r["category"] for r in rows)
    actual_complete = bool(rows) and all(row["status"] == "accepted" for row in rows)
    if ledger["coverage"]["all_required_mappings_accepted"] != actual_complete:
        errors.append("Coverage summary does not match required row states")
    for category, count in expected.items():
        if counts[category] != count:
            errors.append(f"Baseline lost/duplicated rows for {category}: {counts[category]} != {count}")
    if baseline["source_files"] != 374 or baseline["source_unique_hashes"] != 365 or baseline["source_bytes"] != 503081481:
        errors.append("Verified original snapshot totals changed")
    if any(len(r["reference_detail"]["menu_lengths"]) != 5 for r in rows if r["category"] == "courses"):
        errors.append("Missing course level variants")
    scans = 0
    if scan:
        for folder in ["Assets", "ArtSource"]:
            for path in (ROOT / folder).rglob("*"):
                if path.is_file() and path.suffix not in [".meta", ".blend1", ".blend2"]:
                    scans += 1
                    if sha(path) in original_hashes:
                        errors.append("Original file copied into production tree: " + path.relative_to(ROOT).as_posix())
    return {"validation_passed": not errors, "errors": errors, "bound_files_checked": len(verified_paths),
            "production_files_scanned_for_exact_source_copy": scans,
            "content_acceptance_passed": actual_complete and not errors,
            "state_counts": dict(sorted(Counter(r["status"] for r in rows).items())),
            "limitations": ["Exact hashes cannot detect transformed reference media; production source/provenance review is also required.",
                            "No aggregate independent asset count or global content-completion percentage is claimed.",
                            "Build output is not scanned here; build receipt/provenance and runtime integration are separate acceptance evidence."]}


def csv_text(ledger):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["id", "category", "label", "reference_unit", "semantic_independence_verified", "reference_files",
                     "status", "replacement_ids", "build_packs", "remaining_work"])
    for r in ledger["entries"]:
        writer.writerow([r["id"], r["category"], r["label"], r["reference_unit"], r["semantic_independence_verified"],
                         ";".join(r["reference_files"]), r["status"], ";".join(r["replacement_ids"]),
                         ";".join(r["build_packs"]), r["remaining_work"]])
    return output.getvalue()


def markdown(ledger):
    b = ledger["baseline"]
    lines = ["# P08 ContentParityLedger", "", "Generated by `python tools/p08/content/content_ledger.py --write`. This is an evidence register; validation PASS does not mean P08 content acceptance.", "",
             "Original files remain research-only. Every source reference includes SHA-256 in the JSON. Production paths, authoring source, concepts, provenance and QA references are hash-bound separately.", "",
             "## Verified baseline", "", "| Group | Baseline | Count meaning |", "|---|---:|---|",
             "| Courses | 5 families / 25 level variants | Five original course containers; level metadata is not 25 independent track meshes |",
             "| Bikes | 15 SKU | 15 SPEC/commerce definitions; mesh/chassis independence must be declared |",
             "| Characters | 8 identities / 24 portraits | Three N/H/F source states; runtime roster can have additional identities |",
             "| Family references | 163 | Compound containers; independent traffic/scenery/pedestrian concepts remain unresolved |",
             f"| Image reference files | {b['image_files']} files / {b['image_unique_hashes']} unique hashes | Includes bike/portrait/UI views already represented by other roles; never add to those counts |",
             "| Horizons / dashboards | 5 / 3 | Hi/Lo and metric/imperial variants share roles |",
             "| Typography / localization | 4 source fonts / 5 bundles | Production typography may share one licensed family; five-language copy remains an explicit coverage requirement |"]
    for name, key in [("SFX", "sfx"), ("PCM music", "pcm_music"), ("Cinematics", "cinematics")]:
        m = b[key]
        lines.append(f"| {name} | {m['files']} files / {m['unique_file_hashes']} unique hashes | {m['gross_seconds']} s gross; {m['deduplicated_seconds']} s deduplicated |")
    lines += ["| MIDS / soundbanks | 11 / 6 | Composition/arrangement equivalence is unresolved; do not add these to 14 PCM tracks as 25 compositions |", "",
              "Durations above come from ffprobe format metadata after full decoding. They quantify the reference library, not a mandate to pad replacement media. Byte totals (503,081,481 source bytes) and sprite/LOD/mip/frame totals do not establish meaningful content parity.", "",
              "## Current coverage", "", f"State counts: `{json.dumps(ledger['coverage']['state_counts'], sort_keys=True)}`. Full required mapping accepted: **{str(ledger['coverage']['all_required_mappings_accepted']).upper()}**.", "",
              "P03–P07 sources supply a playable canyon slice, original rider/patrol/cars/props, 12 rider animation clips, 17 audio clips, licensed typography and functional UI. Those implementations are mapped only to the roles their evidence supports. A shared motorcycle is not 15 accepted designs. One pedestrian does not close every FAM with an authoring-name hint. The P06 gameplay QA capture is not an authored event cinematic.", "",
              "P08 media authoring now supplies 72 new synthesized cues, 14 full new compositions, 11 additional short scores, and 59 declarative real-time sequences. Their source, runtime audio, compiled direction and signal audits are mapped explicitly; semantic review, human listening, actual director playback, Unity/browser integration and quality gates remain partial. See [media handoff](../media/README.md). Neither a passing waveform check nor a distinct camera signature establishes creative or gameplay acceptance.", "",
              "Remaining production work includes course/biome and level integration; bike/character/traffic/props production and acceptance; the unresolved source semantic catalog; equipment/animation state coverage; UI scene/status/localization variety; and actual audio/cinematic integration and review. Each unresolved reference has its own row below or in the machine-readable ledger.", "",
              "## Semantic groups and outstanding rows", "", "| Group | Rows (not independent assets) | Accepted | Other |", "|---|---:|---:|---|"]
    groups = defaultdict(list)
    for row in ledger["entries"]:
        groups[row["category"]].append(row)
    for group, rows in sorted(groups.items()):
        counts = Counter(r["status"] for r in rows)
        lines.append(f"| {group} | {len(rows)} | {counts['accepted']} | {dict(counts)} |")
    lines += ["", "## Reproduce and close evidence", "", "```powershell", "python tools/p08/content/content_ledger.py --write", "python tools/p08/content/content_ledger.py --check", "python tools/p08/content/content_ledger.py --check --require-complete", "python -m unittest discover -s tools/p08/content -p test_*.py", "```", "",
              "`--write` refreshes hashes and deterministic JSON/CSV/Markdown from the audited baseline plus `production-mappings.json`. `--check` rejects stale/missing paths, baseline loss, duplicate IDs and whole-file copies of reference media in Assets/ArtSource. `--require-complete` additionally fails if any required row is not accepted. Pending entries remain pending until an explicit mapping, production source, build pack and real QA evidence support acceptance.", "",
              "`reference-baseline.json` retains portable audit metadata, source hashes and upstream audit hashes so a checkout does not depend on gitignored extracted research files. `--capture-reference` refreshes this snapshot only from the existing local P00/P01 audit JSON. It never copies image/audio/video/source payload bytes. `--source-root <original-folder>` optionally rechecks all 374 original file paths and hashes read-only.", "",
              "The machine-readable JSON preserves every individual reference including all 163 unresolved family rows, 72 SFX, 14 unique PCM files, 11 MIDS and 59 unique cinematics. Filename-family hints remain hints. A reviewer must examine source/runtime context before claiming event equivalence; unknowns must not be renamed as verified semantics.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--capture-reference", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    if args.capture_reference:
        capture_reference()
        print("Metadata-only reference baseline captured; run --write then --check.")
        return 0
    ledger = build()
    rendered = {"ContentParityLedger.json": json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
                "ContentParityLedger.csv": csv_text(ledger), "ContentParityLedger.md": markdown(ledger)}
    if args.write:
        OUT.mkdir(parents=True, exist_ok=True)
        for filename, text in rendered.items():
            (OUT / filename).write_text(text, encoding="utf-8", newline="\n")
    stale = []
    for filename, text in rendered.items():
        path = OUT / filename
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            stale.append("Stale generated ledger artifact: " + filename)
    report = inspect(ledger)
    if args.source_root:
        base = args.source_root.resolve()
        verified = 0
        for original in ledger["reference_source_files"]:
            path = (base / original["path"]).resolve()
            if not path.is_relative_to(base) or not path.is_file() or path.stat().st_size != original["bytes"] or sha(path) != original["sha256"]:
                report["errors"].append("Original reference changed/missing: " + original["path"])
            else:
                verified += 1
        report["original_reference_files_reverified_read_only"] = verified
    report["errors"].extend(stale)
    report["validation_passed"] = not report["errors"]
    report["ledger_sha256"] = sha(OUT / "ContentParityLedger.json") if (OUT / "ContentParityLedger.json").exists() else None
    if args.write:
        (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    return 0 if report["validation_passed"] and (not args.require_complete or report["content_acceptance_passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
