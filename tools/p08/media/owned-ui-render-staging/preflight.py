"""Source-bound managed compile of the owned UI fixture; never invokes Unity."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANAGED = Path('C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/Managed/UnityEngine')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs = [HERE / name for name in ('OwnedUiRenderFixture.cs', 'ProtectedUiFonts.cs', 'Preflight.csproj', 'preflight.py')]
    inputs += sorted(MANAGED.glob('*.dll'))
    inputs += [ROOT / 'Library/ScriptAssemblies/Unity.Collections.dll',
               ROOT / 'Library/PackageCache/com.unity.nuget.newtonsoft-json@4dfd81071c64/Runtime/Newtonsoft.Json.dll',
               ROOT / 'Assets/RacingBois/Settings/MainPanel.asset', ROOT / 'Assets/RacingBois/Settings/MainPanel.asset.meta',
               ROOT / 'docs/p08/media/global-copy-character-corpus-20260928.json']
    inputs += sorted(path for path in (ROOT / 'Assets/RacingBois/UI').rglob('*') if path.is_file())
    inputs += [ROOT / 'Library/ScriptAssemblies' / name for name in ('RacingBois.Client.Application.dll', 'RacingBois.Client.Adapters.dll',
               'RacingBois.Client.Presentation.dll', 'RacingBois.Client.Bootstrap.dll', 'RacingBois.Authoring.Editor.dll')]
    before = {str(path.resolve()): sha(path) for path in inputs}
    result = subprocess.run(['dotnet', 'build', str(HERE / 'Preflight.csproj'), '--nologo', '-v:minimal'], cwd=ROOT, capture_output=True, text=True)
    after = {str(path.resolve()): sha(path) for path in inputs}
    changed = [path for path in before if before[path] != after[path]]
    dll = HERE / 'bin/Debug/netstandard2.1/RacingBois.Tools.OwnedUiRender.dll'
    report = dict(schema=1, passed=result.returncode == 0 and not changed, compilation=result.stdout + result.stderr,
                  inputHashesBefore=before, inputHashesAfter=after, changedInputs=changed,
                  helperDllSha256=sha(dll) if dll.exists() else None, nativeFontCopyVerified=False, nativeRenderedUiVerified=False,
                  scope='Managed compile against installed Unity modules; compiler and integration/source inputs hashed before/after. No Unity/Assets action, native ownership, rendering, original-font acceptance or release acceptance.')
    (HERE / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=report['passed'], changedInputs=changed, nativeRenderedUiVerified=False)))
    if result.returncode:
        print(result.stdout + result.stderr)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
