"""Build the separate native driver after root freezes production assemblies."""
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
    files = [HERE / 'AttachedUiDriver.cs', HERE / 'Driver.csproj', HERE / 'preflight.py',
             HERE.parent / 'native-ui-contract-staging/Fixtures.cs',
             HERE.parent / 'global-copy-pristine-amendment/authored-text-union.json',
             ROOT / 'docs/p08/media/global-copy-pristine-r2-compiled-sources-20260928.json',
             HERE.parent / 'owned-ui-render-r2-staging/bin/Debug/netstandard2.1/RacingBois.Tools.OwnedUiRenderR2.dll',
             ROOT / 'Library/PackageCache/com.unity.nuget.newtonsoft-json@4dfd81071c64/Runtime/Newtonsoft.Json.dll']
    files += [ROOT / 'Library/ScriptAssemblies' / name for name in ('RacingBois.Client.Application.dll', 'RacingBois.Client.Adapters.dll', 'RacingBois.Client.Presentation.dll',
              'RacingBois.Client.Bootstrap.dll', 'RacingBois.Protocol.dll', 'RacingBois.Gameplay.Definitions.dll')]
    files += sorted(MANAGED.glob('*.dll'))
    before = {str(path.resolve()): sha(path) for path in files}
    result = subprocess.run(['dotnet', 'build', str(HERE / 'Driver.csproj'), '--nologo', '-v:minimal'], cwd=ROOT, capture_output=True, text=True)
    after = {str(path.resolve()): sha(path) for path in files}
    changed = [path for path in before if before[path] != after[path]]
    dll = HERE / 'bin/Debug/netstandard2.1/RacingBois.Tools.AttachedUiDriverR2.dll'
    report = dict(schema=1, passed=result.returncode == 0 and not changed, compilation=result.stdout + result.stderr, inputHashesBefore=before, inputHashesAfter=after,
                  changedInputs=changed, driverSha256=sha(dll) if dll.exists() else None, nativeExecuted=False,
                  scope='Managed driver compile and stable input binding only. Root must run actual attached-panel capture and inspect images; no native rendering/focus/full-game acceptance from this report.')
    (HERE / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=report['passed'], changedInputs=changed, nativeExecuted=False)))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
