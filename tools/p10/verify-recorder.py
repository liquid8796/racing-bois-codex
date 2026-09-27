"""Source-bound policy/verifier tests and managed compile checks for the native observer."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def inventory():
    project = ROOT / "tools/p08/desktop/RuntimeCompile.csproj"
    files = {project, ROOT / "tools/p08/desktop/preflight_runtime.py"}
    for node in ET.parse(project).iter("Compile"):
        include = node.attrib["Include"].replace("$(ProjectRoot)", str(ROOT) + "/")
        files.add(Path(include))
    for relative in ("tools/p10/RecorderConfigTests",):
        files.update(path for path in (ROOT / relative).glob("*") if path.suffix in (".cs", ".csproj"))
    files.update(ROOT / "tools/p10" / name for name in ("verify-recorder.py", "verify-player-qa.py", "prepare-player-qa.py", "test_player_qa.py"))
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}


def main():
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = ROOT / "docs/p10/recorder" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    private = ROOT / "_local/p10/recorder" / run_id
    private.mkdir(parents=True, exist_ok=False)
    before = inventory()
    cases = []
    commands = [
        ("configuration", ["dotnet", "run", "--project", "tools/p10/RecorderConfigTests", "-c", "Release", "--", str(directory / "configuration.json")]),
        ("raw_evidence_verifier", [sys.executable, "tools/p10/test_player_qa.py"]),
        ("managed_branches", [sys.executable, "tools/p08/desktop/preflight_runtime.py"]),
    ]
    for name, command in commands:
        with (private / (name + ".log")).open("wb") as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        cases.append({"name": name, "passed": result.returncode == 0, "exitCode": result.returncode})
        print(name, "PASS" if result.returncode == 0 else "FAIL", flush=True)
    config = json.loads((directory / "configuration.json").read_text())
    compile_path = ROOT / "docs/p08/desktop/runtime-compile-preflight.json"
    compiled = json.loads(compile_path.read_text())
    after = inventory()
    changes = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    passed = all(case["passed"] for case in cases) and config["passed"] == 9 and config["failed"] == 0 and compiled["passed"] and len(compiled["compilations"]) == 3
    receipt = {"schema": 1, "generatedUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "runId": run_id,
        "status": "FAIL" if not passed else "SUPERSEDED" if changes else "PASS", "sourceStable": not changes, "changedSources": changes, "sources": before,
        "configurationTests": 9, "rawEvidenceTests": 8, "managedBranches": 3, "cases": cases, "compileReceiptSha256": hashlib.sha256(compile_path.read_bytes()).hexdigest(),
        "scope": "Pure .NET policy, negative synthetic raw-verifier fixtures and Roslyn against installed Unity assemblies. Not Unity lifecycle, actual player timing, visual/input acceptance or full release completion."}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    (directory / "managed-compilation.json").write_text(json.dumps(compiled, indent=2), encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in ("runId", "status", "changedSources")}), flush=True)
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
