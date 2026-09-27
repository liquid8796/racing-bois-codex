"""Validate live file bindings without pretending to render Unity UI outside Unity."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
FILES=["Assets/RacingBois/UI/Race.uxml","Assets/RacingBois/UI/Career.uss",
       "Assets/RacingBois/Client/Presentation/CareerView.cs","Assets/RacingBois/Client/Presentation/MultiplayerLobbyView.cs",
       "Assets/RacingBois/Client/Presentation/RaceScreen.Content.cs"]


def main():
    errors=[]
    document=ET.fromstring((ROOT/FILES[0]).read_text(encoding="utf-8"))
    names=[element.attrib["name"] for element in document.iter() if "name" in element.attrib]
    if len(names)!=len(set(names)):errors.append("Duplicate UXML name identifiers")
    bound=[]
    for relative in [FILES[3],FILES[4]]:
        code=(ROOT/relative).read_text(encoding="utf-8")
        for name in sorted(set(re.findall(r'\.Q(?:<[^>]+>)?\("([^"\n]+)"\)',code))):
            if name not in names:errors.append("Missing UXML target: "+relative+" -> "+name)
            bound.append(dict(source=relative,name=name,present=name in names))
    tags={element.attrib.get("name"):element.tag.rsplit("}",1)[-1] for element in document.iter()}
    for name in ["mp-course","mp-level","practice-course","practice-level","practice-bike","practice-character"]:
        if tags.get(name)!="DropdownField":errors.append("Expected dropdown target: "+name)
    for name in ["practice-panel","content-loading","gallery-open"]:
        if name not in names:errors.append("Existing P08 overlay/control was removed: "+name)
    styles=(ROOT/FILES[1]).read_text(encoding="utf-8")
    if styles.count("{")!=styles.count("}"):errors.append("Career USS has unbalanced rule blocks")
    for name in ["career-character-grid","career-character-card","career-character-portrait","career-bike-stats","career-portrait-state"]:
        if not re.search(r'\.'+re.escape(name)+r'(?![\w-])',styles):errors.append("Missing new career style: "+name)
    report=dict(passed=not errors,errors=errors,uniqueUxmlNames=len(names),checkedBindings=len(bound),bindings=bound,
                sourceFiles=[dict(path=relative,sha256=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()) for relative in FILES],
                scope="Actual UXML parse, name uniqueness, named field/control bindings and stylesheet block/selectors only. Not a Unity render, focus, click or browser acceptance receipt.")
    (ROOT/"docs/p08/media/ui-binding-validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:value for key,value in report.items() if key not in ["bindings","sourceFiles"]}))
    return 0 if report["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
