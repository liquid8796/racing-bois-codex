"""Compile both Unity platform branches and bind exact source hashes; no Editor calls."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def main():
    results=[]
    for symbol in ["UNITY_EDITOR","UNITY_WEBGL"]:
        process=subprocess.run(["dotnet","build","tools/p08/media/RuntimeCompile","-p:DefineConstants="+symbol,"--nologo","-v:minimal"],cwd=ROOT,capture_output=True,text=True)
        results.append(dict(define=symbol,passed=process.returncode==0,exitCode=process.returncode,output=process.stdout+process.stderr))
        print(symbol,"PASS" if process.returncode==0 else "FAIL",flush=True)
    paths=["Assets/RacingBois/Client/Adapters/P08MusicDirector.cs","Assets/RacingBois/Client/Bootstrap/BootstrapCinematicCoordinator.cs",
           "Assets/RacingBois/Client/Application/CinematicCatalog.cs","Assets/RacingBois/Plugins/WebGL/RacingBoisMusic.jslib"]
    paths.extend(path.relative_to(ROOT).as_posix() for path in (ROOT/"Assets/RacingBois/Client/Presentation").glob("Cinematic*.cs"))
    paths.extend(["Assets/RacingBois/Client/Presentation/CareerView.cs","Assets/RacingBois/Client/Presentation/MultiplayerLobbyView.cs",
                  "Assets/RacingBois/UI/Career.uss","Assets/RacingBois/UI/Race.uxml"])
    report=dict(passed=all(r["passed"] for r in results),unityReferenceVersion="6000.5.7f1",
                sourceFiles=[dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()) for path in sorted(paths)],compilations=results,
                scope="Roslyn preflight against installed Unity Engine modules and current project assemblies for Editor and WebGL conditional branches. This is not a Unity import, IL2CPP build, Play mode, browser or visual acceptance receipt.")
    (ROOT/"docs/p08/media/runtime-compile-preflight.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    if not report["passed"]:return 1
    return subprocess.run(["node","tools/p08/media/test_music_bridge.mjs"],cwd=ROOT).returncode


if __name__=="__main__":
    raise SystemExit(main())
