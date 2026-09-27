"""Compile the isolated golden review infrastructure without launching Unity."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    project = ROOT / "tools/p08/golden/importer-preflight.csproj"
    inputs = sorted(
        list((ROOT / "Assets/RacingBois/Editor").glob("GoldenSampleBuilder*.cs"))
        + list((ROOT / "Assets/RacingBois/Editor").glob("NativeBuild*.cs"))
        + list((ROOT / "Assets/RacingBois/Golden/Runtime").glob("*.cs"))
        + [ROOT / "Assets/RacingBois/Editor/UrpProfileAuthoring.cs", ROOT / "Assets/RacingBois/Client/Presentation/RiderAnimationSet.cs", ROOT / "Assets/RacingBois/Golden/Runtime/RacingBois.Golden.asmdef",
           ROOT / "Assets/RacingBois/Editor/RacingBois.Authoring.Editor.asmdef", project, Path(__file__)]
    )
    before = [(path.relative_to(ROOT).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()) for path in inputs]
    result = subprocess.run(["dotnet", "build", str(project), "--nologo", "-v:minimal"],
                            cwd=ROOT, capture_output=True, text=True)
    unchanged = all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in before)
    receipt = {
        "schema": 1,
        "utc": datetime.now(timezone.utc).isoformat(),
        "passed": result.returncode == 0 and unchanged,
        "sourceBindingPassed": unchanged,
        "exitCode": result.returncode,
        "unityReferenceVersion": "6000.5.7f1",
        "scope": "Managed compiler against installed Unity assemblies only; no Unity import, scene, visual, build or player acceptance.",
        "inputs": [{"path": path, "sha256": digest} for path, digest in before],
        "output": result.stdout + result.stderr,
    }
    output = ROOT / "docs/p08/golden/unity/compiler-preflight.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
