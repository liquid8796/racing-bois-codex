"""Extract bounded summaries and freeze staged Garage V7 evidence."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/p08/golden/garage/v7"


def extract(path, marker):
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for child in value.values():
                yield from strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from strings(child)

    receipt = json.loads(path.read_text(encoding="utf-8-sig"))
    for value in strings(receipt):
        index = value.find(marker)
        if index >= 0:
            return json.JSONDecoder().raw_decode(value[index + len(marker):].lstrip())[0]
    raise ValueError(f"No {marker} in {path}")


def fingerprint(relative):
    path = ROOT / relative
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


source = extract(OUT / "exact-source-retry-mcp.json", "GARAGE_V7_EXPLICIT_TRIANGLES ")
roundtrip = extract(OUT / "roundtrip-mcp.json", "GARAGE_V7_ROUNDTRIP ")
assert source["positionsUvMaterialsTransformsExact"] and roundtrip["passed"]
assert source["meshCount"] == roundtrip["meshes"] == 180
assert source["triangles"] == roundtrip["triangles"] == 165812
for name, report in [("source-preservation.json", source), ("roundtrip.json", roundtrip)]:
    (OUT / name).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
baseline = fingerprint("ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage.blend")
assert baseline["sha256"] == "b7eddebc4be6808262cee601f6737a949c8535b6b98abd7f81b0ab2b1fa0eb79"
protected = fingerprint("ArtSource/Weapons/RB_Club.blend")
assert protected["sha256"] == "553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f"
delivery = {
    "schema": 1,
    "source": fingerprint("ArtSource/P08/Golden/Garage/V7/RB_Golden_Garage.blend"),
    "fbx": fingerprint("_local/p08-garage-v7-staging/RB_Golden_Garage.fbx"),
    "preservedV5": baseline,
    "protectedClubUnchanged": True,
    "stagingOnly": True,
    "assetsWritten": False,
    "nativeImportedByThisTask": False,
    "visualAccepted": False,
    "integration": "Root owns native Unity probe. Copy to a fresh V7 Assets path, preserve FBX SHA256, and bind a new descriptor/module-map. Existing V5 and V6 remain historical evidence.",
    "sourcePreservation": {
        "meshCount": source["meshCount"], "triangles": source["triangles"],
        "positionsUvMaterialsTransformsExact": True,
        "triangleStream": "Exact V5 mesh.loop_triangles order, made explicit before export",
        "normalsBitExact": source["allNormalsBitExact"],
        "meshesWithNormalEncodingDeviation": sum(not row["normalFloat32BitsExact"] for row in source["objects"]),
        "maximumNormalComponentDeviation": source["maximumNormalComponentDeviation"],
        "maximumNormalAngularDeviationDegrees": source["maximumNormalAngularDeviationDegrees"],
    },
    "fbxRoundtrip": {key: value for key, value in roundtrip.items() if key != "objects"},
    "uvContract": {
        "UV0_MetricTile": "Unchanged repeating metric projection; intentional overlap and coordinates outside 0..1",
        "LightmapUV": "Exact authored per-corner values on all 60 LOD0 meshes; absent on lower LODs as before",
        "threshold": "UV absolute 2D cross >1e-14; physical world-metre squared cross >1e-16",
    },
    "materials": "Unchanged V5 baseline materials and textures. Not the separate coat-comparison source.",
    "proofs": [fingerprint("docs/p08/golden/garage/v7/" + name) for name in [
        "source-preservation.json", "roundtrip.json", "exact-source-retry-mcp.json", "export-mcp.json", "roundtrip-mcp.json"]],
    "scripts": [fingerprint("tools/p08/golden/" + name) for name in [
        "garage_exact_triangles_v7.py", "garage_export_v7.py", "garage_roundtrip_v7.py"]],
}
(OUT / "delivery.json").write_text(json.dumps(delivery, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in delivery.items() if key in ["source", "fbx", "sourcePreservation", "fbxRoundtrip", "protectedClubUnchanged"]}, indent=2))
