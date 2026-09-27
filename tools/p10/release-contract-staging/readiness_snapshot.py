"""Read-only content/release evidence snapshot; writes only a new report.

No Unity/Blender operation, network request, art promotion or runtime mutation.
An internally consistent receipt is not independent visual or player acceptance.
"""
from pathlib import Path
import collections
import csv
import datetime as dt
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/p08/release-readiness-20260927"


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def sha(name):
    path = ROOT / name
    if not path.is_file():
        return None
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def bound(name):
    path = ROOT / name
    return {"path": name, "exists": path.is_file(), "sha256": sha(name), "bytes": path.stat().st_size if path.is_file() else None}


ledger = load("docs/p08/content/ContentParityLedger.json")
audio = load("docs/p08/media/audio-delivery.json")
soak_path = "docs/p10/network/20260927T003037Z/run.json"
soak = load(soak_path)
soak_before = {name: sha(name) for name in soak["sources"]}

ledger_inputs = {}
for row in ledger["inputs"]:
    ledger_inputs[row["path"]] = row["sha256"]
for asset in ledger["production_assets"]:
    for field in ["production_paths", "authoring_paths", "concept_paths", "provenance_paths", "qa_paths"]:
        for row in asset[field]:
            ledger_inputs[row["path"]] = row["sha256"]
ledger_mismatches = [{"path": path, "expected": expected, "actual": actual}
                     for path, expected in sorted(ledger_inputs.items()) if (actual := sha(path)) != expected]
audio_mismatches = []
for row in audio["clips"]:
    actual = sha(row["oggPath"])
    if actual != row["oggSha256"]:
        audio_mismatches.append({"id": row["id"], "path": row["oggPath"], "expected": row["oggSha256"], "actual": actual})
audio_receipt_mismatches = [key for key in ["audioManifest", "audioAudit"] if sha(audio[key]) != audio[key + "Sha256"]]

paths = ["Assets/RacingBois/Content/P08", "Assets/StreamingAssets/Content", "Build/Content-editor",
         "Build/Content-desktop", "Build/Desktop-P08", "docs/p08/desktop/build.json"]
source_text = (ROOT / "Packages/com.racingbois.foundation/Runtime/Definitions/ProductionContent.cs").read_text()
masks = {name: int(value) for name, value in re.findall(r"public const int (Available\w+Mask) = (\d+);", source_text)}
expected_masks = {"AvailableRouteMask": 31, "AvailableBikeArtMask": 32767, "AvailableCharacterArtMask": 255}
legacy_bikes = [f"Assets/RacingBois/Prefabs/P08/RB_P08_Bike_{i:02}.prefab" for i in range(15)]
portraits = [f"Assets/RacingBois/Art/P08/Portraits/RB_P08_Portrait_{i:02}_{state:02}.png" for i in range(8) for state in range(3)]
garage_path = "docs/p08/golden/garage/v7/native-primary-uv.csv"
with (ROOT / garage_path).open(encoding="utf-8-sig", newline="") as stream:
    garage = list(csv.DictReader(stream))
wan = load("docs/p10/network/20260927T003126Z/run.json")
wan_probe = load("docs/p10/network/20260927T003126Z/probe.json")
native = load("docs/p10/native-wss/turnover-20260927-0727.json")
deployment = load("docs/p09/releases/f/deployment-after-soak.json")

evidence_names = ["docs/PHASE_PLAN.md", "docs/p08/parity-audit-20260927/REPORT.md",
    "docs/p08/content/ContentParityLedger.json", "docs/p08/content/production-mappings.json",
    "docs/p08/media/audio-delivery.json", "Assets/RacingBois/Editor/P08ContentPackBuilder.cs",
    "Assets/RacingBois/Editor/P08DesktopBuilder.cs", "Assets/RacingBois/Client/Presentation/P08ActorContent.cs",
    "Assets/RacingBois/Client/Presentation/P08RouteContent.cs", "Assets/RacingBois/Client/Application/ContentManifestRules.cs",
    "Assets/RacingBois/Client/Adapters/P08ContentLoader.cs", "tools/p08/desktop/audit_desktop.py",
    "tools/p05/publish-lan.ps1", "tools/foundation/publish-lan.ps1", "tools/p07/package-release.py",
    "Packages/com.racingbois.foundation/Runtime/Definitions/ProductionContent.cs", garage_path,
    "docs/p08/golden/garage/v7/descriptor.json", "docs/p09/releases/f/deployment-after-soak.json",
    "docs/p10/network/20260927T003126Z/run.json", "docs/p10/network/20260927T003126Z/probe.json",
    "docs/p10/native-wss/turnover-20260927-0727.json",
    "tools/p10/release-contract-staging/candidate-manifest.json",
    "docs/p08/release-readiness-20260927/staged-verification.json"]
soak_after = {name: sha(name) for name in soak["sources"]}
report = {
    "schema": 1, "utc": dt.datetime.now(dt.timezone.utc).isoformat(), "releaseAccepted": False,
    "scope": "Targeted content/build handoff review. No semantic acceptance inferred from row counts, hashes or technical import.",
    "ledger": {"rows": len(ledger["entries"]), "states": dict(collections.Counter(row["status"] for row in ledger["entries"])),
               "boundPaths": len(ledger_inputs), "staleBindings": ledger_mismatches,
               "allRequiredAcceptedDeclared": ledger["coverage"]["all_required_mappings_accepted"]},
    "audio": {"clips": len(audio["clips"]), "categories": dict(collections.Counter(row["category"] for row in audio["clips"])),
              "oggHashMismatches": audio_mismatches, "deliveryReceiptMismatches": audio_receipt_mismatches,
              "listeningAccepted": sum(row.get("humanListeningAccepted") is True for row in audio["clips"]),
              "runtimeMixAccepted": sum(row.get("runtimeMixAccepted") is True for row in audio["clips"])},
    "builderInputs": {"legacyBikePrefabsMissing": [p for p in legacy_bikes if not (ROOT / p).is_file()],
                      "portraitPathsMissing": [p for p in portraits if not (ROOT / p).is_file()],
                      "note": "Required fixed paths from the current builder; does not count every missing semantic role or authorize placeholder substitutions."},
    "deliveryLocations": {path: (ROOT / path).exists() for path in paths},
    "masks": {"current": masks, "fullCatalogWouldRequire": expected_masks, "promoted": False},
    "garageV7": {"meshes": len(garage), "triangles": sum(int(r["triangles"]) for r in garage),
                 "nativeUv0Degenerate": sum(int(r["badPrimaryUv"]) for r in garage), "visualAccepted": False},
    "operations": {"latestRecordedDeployment": {key: deployment.get(key) for key in ["status", "generatedUtc", "releaseId", "sourceSha256", "verifiedFiles"]},
                   "wan30Minutes": {"runStatus": wan["status"], "sourceStable": wan.get("sourceStable"),
                                    **{key: wan_probe.get(key) for key in ["status", "elapsedSeconds", "peers", "cycles", "reconnects", "storms", "gameplayContentHash"]}},
                   "nativeWssSpecimen": {key: native.get(key) for key in ["status", "finishedUtc", "platform", "backend", "completedRaces", "elapsedSeconds", "maximumCorrectionMeters"]},
                   "limits": "Recorded deployment and single-workstation network specimens only; not live revalidation, full game acceptance, multiregion player proof or physical offline LAN."},
    "eightHourSourceFreeze": {"run": soak_path, "recordedStatus": soak["status"], "sourcePaths": len(soak["sources"]),
                              "currentMismatchToFrozenRun": [name for name, expected in soak["sources"].items() if soak_after[name] != expected],
                              "changedDuringThisReadOnlySnapshot": [name for name in soak_before if soak_before[name] != soak_after[name]],
                              "finalPassNotInferred": True},
    "evidence": [bound(name) for name in evidence_names], "globalCompletionPercentage": None,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "snapshot.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"ledgerStates": report["ledger"]["states"], "staleLedgerBindings": len(ledger_mismatches),
                  "audioOggHashMismatches": len(audio_mismatches), "missingBikePrefabPaths": len(report["builderInputs"]["legacyBikePrefabsMissing"]),
                  "missingPortraitPaths": len(report["builderInputs"]["portraitPathsMissing"]), "locations": report["deliveryLocations"],
                  "garageV7": report["garageV7"], "eightHourSourceFreeze": report["eightHourSourceFreeze"]}, indent=2))
