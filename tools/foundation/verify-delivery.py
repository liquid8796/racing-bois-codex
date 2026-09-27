"""Verify P01/P02 delivery evidence and exact deployed-package Web hashes."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    original = read("docs/reverse-engineering/assets/source_manifest.json")
    original_hashes = {item["sha256"] for item in original}
    asset_files = [p for p in (ROOT / "Assets").rglob("*") if p.is_file()]
    copied = [p.relative_to(ROOT).as_posix() for p in asset_files if sha(p) in original_hashes]
    check(not copied, "Original source-file hash found in Unity Assets: " + str(copied))
    logic = read("docs/p01/logic/verification.json")
    check(logic["status"] == "PASS" and logic["all_original_files_verified"] == 374, "P01 logic/integrity receipt failed")
    tests = read("docs/p02/backend/foundation-tests.json")
    check(tests["failed"] == 0 and tests["passed"] >= 18, "Foundation tests failed/incomplete")
    build = read("docs/p02/unity/final-build.json")
    check(build["result"] == "Succeeded" and build["errors"] == 0 and build["warnings"] == 0, "Final Unity build not clean")
    prefab = read("docs/p02/unity/asset-validation.json")
    check(prefab["passed"] and prefab["lodCount"] == 3 and prefab["colliders"] == 1 and prefab["uv2"], "Prefab validation incomplete")
    view = read("docs/p02/unity/view-lifecycle.json")
    check(view["passed"] and view["renderersCreated"] == 0, "Disconnected-view lifecycle failed")
    browser = read("docs/p02/browser-final.json")
    check(browser["sample"]["state"] == "Connected" and browser["sample"]["peers"] == 2 and browser["sample"]["sharedFixture"], "Final browser evidence incomplete")
    check(not browser["consoleErrors"] and not browser["consoleWarnings"], "Browser reported errors/warnings")
    arm = read("docs/p02/oci/arm64-smoke.json")
    check(arm["status"] == "PASS" and arm["architecture"] == "Arm64", "OCI ARM64 execution missing")
    publish = read("docs/p02/backend/publish-evidence.json")
    web_relative = (ROOT / "Build/current-web.txt").read_text().strip()
    web_root = ROOT / web_relative
    web_hashes = {p.relative_to(web_root).as_posix(): sha(p) for p in web_root.rglob("*") if p.is_file()}
    check("index.html" in web_hashes, "Live Web payload missing")
    check(len(publish["outputs"]) == 2, "Expected Windows and ARM packages")
    for package in publish["outputs"]:
        check(package["selfContained"] and package["includesUnityWeb"] and package["excludesDoNotShip"], "Incomplete package " + package["runtime"])
        root = ROOT / package["relativePath"] / "web"
        actual = {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*") if p.is_file()}
        check(actual == web_hashes, "Package Web payload differs from live version: " + package["runtime"])
        check(all(actual.get(f["path"], "").upper() == f["sha256"].upper() for f in package["webFiles"]), "Publish receipt hash mismatch")
    result = {
        "status": "FAIL" if errors else "PASS",
        "verifiedAtUtc": datetime.now(timezone.utc).isoformat(),
        "sourceCommit": browser["sourceCommit"], "webRoot": web_relative,
        "unityAssetFilesChecked": len(asset_files), "originalAssetHashMatches": copied,
        "nativeLogicFixtures": logic["total_instruction_fixture_cases"],
        "foundationTestsPassed": tests["passed"], "webFiles": len(web_hashes),
        "selfContainedPackages": len(publish["outputs"]), "errors": errors,
        "limits": "Integrity/evidence checks, not proof of 100% original logic. Hash differences alone do not prove new authorship; retained recipe and Blender QA provide that evidence."
    }
    (ROOT / "docs/p02/delivery-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
