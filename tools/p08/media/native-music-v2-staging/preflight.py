"""Managed compilation only. Never claims native playback or writes to Assets."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANAGED = Path('C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/Managed')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs = [HERE / name for name in ['P08MusicDirector.cs', 'NativeMusicProbe.cs', 'ProbeReceipt.cs', 'Preflight.csproj', 'ProbeCompile.csproj', 'SerializationTests.csproj', 'SerializationTests.cs', 'Directory.Build.props', 'preflight.py']]
    inputs += [ROOT / path for path in ['Assets/RacingBois/Client/Adapters/DesktopConfiguration.cs', 'Assets/RacingBois/Client/Application/DesktopRuntimeConfig.cs',
                                      'Library/ScriptAssemblies/RacingBois.Client.Adapters.dll', 'Library/ScriptAssemblies/RacingBois.Client.Application.dll']]
    inputs += sorted((MANAGED / 'UnityEngine').glob('*.dll'))
    inputs += [ROOT / 'Library/PackageCache/com.unity.nuget.newtonsoft-json@4dfd81071c64/Runtime/Newtonsoft.Json.dll',
               ROOT / 'Assets/RacingBois/Art/P08/Audio/Music/RB_P08_freight-of-light.ogg',
               ROOT / 'tools/p08/media/native-music-staging/fixtures/finite-87055f90f631a745db5312e662525cb14c6c72d0e97a80f5c6ca9fb0606c2464.ogg']
    before = {str(path): sha(path) for path in inputs}
    compilations = []
    for project, symbol in [('Preflight.csproj', 'UNITY_EDITOR'), ('Preflight.csproj', 'UNITY_STANDALONE_WIN'), ('Preflight.csproj', 'UNITY_WEBGL'), ('ProbeCompile.csproj', 'UNITY_EDITOR')]:
        result = subprocess.run(['dotnet', 'build', str(HERE / project), '--nologo', '-v:minimal', '-p:DefineConstants=' + symbol], cwd=ROOT, capture_output=True, text=True)
        compilations.append(dict(project=project, define=symbol, passed=result.returncode == 0, exitCode=result.returncode, output=result.stdout + result.stderr))
        print(project, symbol, 'PASS' if result.returncode == 0 else 'FAIL', flush=True)
    result = subprocess.run(['dotnet', 'run', '--project', str(HERE / 'SerializationTests.csproj'), '--nologo', '-v:minimal'], cwd=ROOT, capture_output=True, text=True)
    compilations.append(dict(project='SerializationTests.csproj', passed=result.returncode == 0, exitCode=result.returncode, output=result.stdout + result.stderr))
    print('SerializationTests', 'PASS' if result.returncode == 0 else 'FAIL', flush=True)
    after = {str(path): sha(path) for path in inputs}
    changed = [path for path in before if before[path] != after[path]]
    probe = HERE / 'bin/ProbeCompile/netstandard2.1/RacingBois.NativeMusic.ProbeV2.dll'
    report = dict(passed=all(item['passed'] for item in compilations) and not changed, unityReferenceVersion='6000.5.7f1',
                  nativePlaybackVerified=False, sourceInputs=before, inputsAfter=after, changedInputs=changed,
                  compilations=compilations, probeDllSha256=sha(probe) if probe.is_file() else None,
                  scope='Roslyn compile against installed Unity modules and current project assemblies. Actual lifecycle behavior requires root-run NativeMusicProbe; no native, audible, browser or full-game acceptance from this receipt.')
    (HERE / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
