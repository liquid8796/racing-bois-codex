"""Record actual isolated contract tests/managed compilation, not native acceptance."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = ROOT / "docs/p08/release-readiness-20260927"
OUT.mkdir(parents=True, exist_ok=True)


def rows():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in HERE.iterdir() if p.suffix in {".py", ".cs", ".csproj", ".fragment"}}


before = rows()
commands = [[sys.executable, "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_*.py", "-v"],
            ["dotnet", "build", str(HERE / "EditorCompile.csproj"), "-v", "minimal", "--nologo"]]
results = []
for name, command in zip(["contract-tests", "managed-compile"], commands):
    run = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
    log = OUT / (name + ".log")
    log.write_text(run.stdout, encoding="utf-8")
    results.append({"name": name, "exitCode": run.returncode, "log": log.relative_to(ROOT).as_posix(),
                    "logSha256": hashlib.sha256(log.read_bytes()).hexdigest()})
result = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(), "passed": all(r["exitCode"] == 0 for r in results) and rows() == before,
          "scope": "Staged desktop receipt contract fixtures and managed Unity API compile only; no real player build/native dependency capture.",
          "sourceStable": rows() == before, "stagedFiles": before, "results": results, "nativeAccepted": False, "releaseAccepted": False}
(OUT / "staged-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "stagedFiles"}, indent=2))
raise SystemExit(0 if result["passed"] else 1)
