"""Compile real native/Editor/Web branches and inspect actual UI bindings. No rendering claims."""
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UI = ROOT / "Assets/RacingBois/UI"
VIEWS = ["RaceScreen.cs", "RaceScreen.Content.cs", "CareerView.cs", "MultiplayerLobbyView.cs", "CinematicGalleryView.cs", "UiBindingScope.cs", "DesktopDisplaySettings.cs"]


def run():
    errors = []
    tree = ET.parse(UI / "Race.uxml")
    names = {e.attrib["name"]: e.tag.rsplit("}", 1)[-1] for e in tree.iter() if "name" in e.attrib}
    all_names = [e.attrib["name"] for e in tree.iter() if "name" in e.attrib]
    if len(all_names) != len(names):
        errors.append("Duplicate named UXML element")
    bindings = []
    for view in ["RaceScreen.cs", "RaceScreen.Content.cs", "MultiplayerLobbyView.cs"]:
        source = ROOT / "Assets/RacingBois/Client/Presentation" / view
        for kind, name in sorted(set(re.findall(r'\.Q(?:<([^>]+)>)?\("([^"\n]+)"\)', source.read_text(encoding="utf-8")))):
            present = name in names
            correct_type = present and (not kind or names[name] == kind or kind == "VisualElement")
            bindings.append(dict(view=view, name=name, declaredType=kind or "VisualElement", actualType=names.get(name), passed=correct_type))
            if not correct_type:
                errors.append(view + " missing/wrong-type binding " + name)
    styles = []
    for element in tree.iter():
        if element.tag.endswith("Style"):
            path = UI / element.attrib["src"]
            if not path.is_file():
                errors.append("Missing stylesheet " + str(path))
                continue
            text = path.read_text(encoding="utf-8")
            if text.count("{") != text.count("}"):
                errors.append("Unbalanced stylesheet " + path.name)
            styles.append(path)
    concepts = [ROOT / "ArtSource/Concepts/P08/Golden/UI" / (screen + "-v2.png") for screen in ["main", "garage"]]
    concepts += [ROOT / "ArtSource/Concepts/P08/UI" / (screen + "-v1.png") for screen in ["ui-lobby", "ui-hud", "ui-gallery"]]
    for path in concepts:
        if not path.is_file() or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            errors.append("Missing/invalid concept image " + path.name)
    compiles = []
    for define in ["UNITY_STANDALONE_WIN", "UNITY_EDITOR", "UNITY_WEBGL"]:
        result = subprocess.run(["dotnet", "build", "tools/p08/ui/RuntimeCompile.csproj", "-p:DefineConstants=" + define, "--nologo", "-v:minimal"], cwd=ROOT, capture_output=True, text=True)
        compiles.append(dict(define=define, passed=result.returncode == 0, output=result.stdout + result.stderr))
        if result.returncode:
            errors.append("Managed preflight failed " + define)
        print(define, "PASS" if result.returncode == 0 else "FAIL", flush=True)
    sources = [UI / "Race.uxml"] + styles + concepts + [ROOT / "Assets/RacingBois/Client/Presentation" / v for v in VIEWS]
    # Bind additional compiled preview/configuration dependencies to this receipt as well.
    project = ROOT / "tools/p08/ui/RuntimeCompile.csproj"
    for path in re.findall(r'Compile Include="\$\(ProjectRoot\)([^"]+)"', project.read_text(encoding="utf-8")):
        candidate = ROOT / path
        if candidate not in sources:
            sources.append(candidate)
    sources += [project, Path(__file__)]
    report = dict(generatedUtc=datetime.now(timezone.utc).isoformat(), passed=not errors, errors=errors,
        uniqueUxmlNames=len(names), checkedBindings=len(bindings), bindings=bindings, compilations=compiles,
        sources=[dict(path=p.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sources],
        scope="Real UXML parse, typed named binding/style/concept existence, Roslyn compilation against Unity 6000.5.7f1 installed assemblies. Does not prove Unity import, rendered layout, mouse/keyboard/gamepad focus, native display modes, player FPS or visual quality.")
    destination = ROOT / "docs/p08/ui/desktop-ui-preflight.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(dict(passed=not errors, uniqueUxmlNames=len(names), checkedBindings=len(bindings), errors=errors)))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(run())
