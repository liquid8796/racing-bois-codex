"""Copy frozen Ash V7 inputs to fresh Unity review paths without accepting art."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[4]
DOC = ROOT / "docs/p08/golden/ash/v7"
DEST = "Assets/RacingBois/Art/P08/Golden/Ash/V7"


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def checked(ref):
    path = (ROOT / ref["path"]).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != ref["sha256"]:
        raise ValueError("Frozen input missing or changed: " + ref["path"])
    return path


def references(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            yield value
        for item in value.values():
            yield from references(item)
    elif isinstance(value, list):
        for item in value:
            yield from references(item)


def main():
    delivery = json.loads((DOC / "delivery.json").read_text(encoding="utf-8"))
    for ref in references(delivery):
        checked(ref)
    descriptor = json.loads(checked(delivery["descriptor"]).read_text(encoding="utf-8"))
    for ref in references(descriptor):
        checked(ref)
    mapping = {delivery["fbx"]["path"]: DEST + "/RB_Golden_Ash_V7.fbx"}
    mapping.update({ref["path"]: DEST + "/Textures/" + Path(ref["path"]).name for ref in delivery["newTextures"]})
    sources = {ref["path"]: ref for ref in [delivery["fbx"], *delivery["newTextures"]]}
    for old, new in mapping.items():
        target = ROOT / new
        if target.exists() and digest(target) != sources[old]["sha256"]:
            raise ValueError("Refusing to overwrite different review input: " + new)
    for old, new in mapping.items():
        target = ROOT / new
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(checked(sources[old]), target)
        if digest(target) != sources[old]["sha256"]:
            raise ValueError("Copy verification failed: " + new)
    for ref in references(descriptor):
        ref["path"] = mapping.get(ref["path"], ref["path"])
        checked(ref)
    target = DOC / "descriptor.json"
    text = json.dumps(descriptor, indent=2) + "\n"
    if target.exists() and target.read_text(encoding="utf-8") != text:
        raise ValueError("Existing descriptor differs")
    target.write_text(text, encoding="utf-8")
    receipt = {"schema": 1, "stagedDelivery": {"path": "docs/p08/golden/ash/v7/delivery.json", "sha256": digest(DOC / "delivery.json")},
               "descriptor": {"path": "docs/p08/golden/ash/v7/descriptor.json", "sha256": digest(target)},
               "copied": [{"source": old, "path": new, "sha256": sources[old]["sha256"]} for old, new in mapping.items()],
               "visualAccepted": False, "productionPromoted": False,
               "scope": "Exact frozen bytes copied to independent V7 Unity review paths. Native import and visual review are separate gates."}
    (DOC / "unity-publication.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"copied": len(mapping), "descriptor": receipt["descriptor"], "visualAccepted": False}))


if __name__ == "__main__":
    main()
