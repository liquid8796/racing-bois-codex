"""Compile native, Editor and retained Web branches; no Editor/process/network automation."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]


def main():
    results = []
    for symbol in ["UNITY_STANDALONE_WIN", "UNITY_EDITOR", "UNITY_WEBGL"]:
        result = subprocess.run(["dotnet", "build", "tools/p08/desktop/RuntimeCompile.csproj", "-p:DefineConstants=" + symbol, "--nologo", "-v:minimal"], cwd=ROOT, capture_output=True, text=True)
        results.append(dict(define=symbol, passed=result.returncode == 0, exitCode=result.returncode, output=result.stdout + result.stderr))
        print(symbol, "PASS" if result.returncode == 0 else "FAIL", flush=True)
    paths = [
        "Assets/RacingBois/Client/Application/DesktopRuntimeConfig.cs",
        "Assets/RacingBois/Client/Application/ContentManifestRules.cs",
        "Assets/RacingBois/Client/Adapters/DesktopConfiguration.cs",
        "Assets/RacingBois/Client/Adapters/P08ContentLoader.cs",
        "Assets/RacingBois/Client/Adapters/P08MusicDirector.cs",
        "Assets/RacingBois/Client/Adapters/BrowserSocketTransport.cs",
        "Assets/RacingBois/Client/Bootstrap/RaceBootstrap.cs",
        "Assets/RacingBois/Client/Bootstrap/DesktopAcceptanceConfiguration.cs",
        "Assets/RacingBois/Client/Bootstrap/DesktopAcceptanceRecorder.cs",
        "Assets/RacingBois/Client/Bootstrap/BootstrapCinematicCoordinator.cs",
        "Assets/RacingBois/Client/Presentation/RaceStageView.cs",
        "Assets/RacingBois/Client/Presentation/RaceScreen.cs",
        "Assets/RacingBois/Client/Presentation/SceneScrim.cs",
        "Assets/RacingBois/Client/Presentation/RiderAnimationSet.cs",
        "Assets/RacingBois/Client/Presentation/RaceScreen.Content.cs",
        "Assets/RacingBois/Client/Presentation/UiViewState.cs",
        "Assets/RacingBois/Client/Presentation/MultiplayerCopy.cs",
        "Assets/RacingBois/Client/Presentation/CareerView.cs",
        "Assets/RacingBois/Client/Presentation/UiBindingScope.cs",
        "Assets/RacingBois/Client/Presentation/DesktopDisplaySettings.cs",
        "Assets/RacingBois/Client/Presentation/CinematicGalleryView.cs",
        "Assets/RacingBois/Client/Presentation/CinematicDirector.cs",
        "Assets/RacingBois/Client/Presentation/CinematicPoseSampler.cs",
        "tools/p08/desktop/RuntimeCompile.csproj",
        "tools/p08/desktop/RacingBois.runtime.json",
        "src/Tests/RacingBois.DesktopConfig.Tests/Program.cs",
    ]
    report = dict(generatedUtc=datetime.now(timezone.utc).isoformat(), passed=all(r["passed"] for r in results),
                  unityReferenceVersion="6000.5.7f1", compilations=results,
                  sources=[dict(path=p, sha256=hashlib.sha256((ROOT / p).read_bytes()).hexdigest()) for p in paths],
                  scope="Roslyn against installed Unity engine/runtime project assemblies including UNITY_STANDALONE_WIN. Not a Unity import, player build, scene, render, audio-decode or live network acceptance.")
    output = ROOT / "docs/p08/desktop/runtime-compile-preflight.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
