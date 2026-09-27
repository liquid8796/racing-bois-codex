"""Validate source/template completeness and compile staged presentation only."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
doc = json.loads((HERE / 'canonical-source.json').read_text(encoding='utf8'))
keys = set()
for path, expected in doc['fileHashes'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
for row in doc['entries']:
    assert row['key'].startswith('multiplayer.') and row['key'] not in keys
    keys.add(row['key'])
    assert row['vi'] and row['bindings']
    assert len(row['arguments']) == len(set(row['arguments']))
    assert set(re.findall(r'\{([^{}]+)\}', row['vi'])) == set(row['arguments']), row['key']
    assert not re.search(r'[{}]', re.sub(r'\{[^{}]+\}', '', row['vi'])), row['key']
    for binding in row['bindings']:
        assert binding['file'] in doc['fileHashes'] and binding['member'] and binding['sourceExpression']
copy = (HERE / 'MultiplayerCopy.cs').read_text(encoding='utf8')
before_copy = (ROOT / 'Assets/RacingBois/Client/Presentation/MultiplayerCopy.cs').read_text(encoding='utf8')
assert 'const string prefix="Máy chủ từ chối: ";' in copy
assert re.findall(r'case "([^"]+)"', copy) == re.findall(r'case "([^"]+)"', before_copy)
assert 'UiText.ClientMessage(locale,message)' in copy
for name in ('MultiplayerCopy.cs', 'MultiplayerLobbyView.cs'):
    code = (HERE / name).read_text(encoding='utf8')
    used = set(re.findall(r'"(multiplayer\.[a-z0-9.-]+)"', code))
    assert used <= keys, sorted(used - keys)
inputs = [HERE / name for name in ('MultiplayerLobbyView.cs', 'MultiplayerCopy.cs', 'UiText.Multiplayer.Generated.cs', 'Preflight.csproj', 'Directory.Build.props',
                                  'BoundaryChecks.cs', 'BoundaryChecks.csproj', 'canonical-source.json', 'uxml-bindings.json', 'validate.py', 'generate.py', 'template_rules.py')]
inputs += sorted((HERE / 'locales').glob('*.json'))
inputs += [HERE.parent / 'global-copy-main-staging' / name for name in ('UiText.cs', 'DisplayLanguage.cs')]
inputs += [ROOT / name for name in ('Assets/RacingBois/Client/Presentation/UiBindingScope.cs', 'Assets/RacingBois/Client/Presentation/UiViewState.cs',
                                   'Library/ScriptAssemblies/RacingBois.Client.Application.dll', 'Library/ScriptAssemblies/RacingBois.Gameplay.Definitions.dll')]
inputs += sorted(Path('C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/Managed/UnityEngine').glob('*.dll'))
before = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
result = subprocess.run(['dotnet', 'build', str(HERE / 'Preflight.csproj'), '--nologo', '-v:minimal'], cwd=ROOT, capture_output=True, text=True)
checks = subprocess.run(['dotnet', 'run', '--project', str(HERE / 'BoundaryChecks.csproj'), '--nologo', '-v:minimal'], cwd=ROOT, capture_output=True, text=True)
after = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
changed = [path for path in before if before[path] != after[path]]
report = dict(passed=result.returncode == 0 and checks.returncode == 0 and not changed, templateCount=len(keys), serverCodesPreserved=True,
              placeholderSetsPassed=True, fileHashes=doc['fileHashes'], compilation=result.stdout + result.stderr,
              compilerInputsBefore=before, compilerInputsAfter=after, changedInputs=changed,
              boundaryChecks=checks.stdout + checks.stderr, boundaryChecksPassed=checks.returncode == 0,
              multilingualAcceptance=False, nativeUiAcceptance=False,
              scope='Source-bound authored six-locale table, exact placeholder/raw-code/opaque-value checks and staged managed compilation; no independent linguistic or native/rendered UI acceptance.')
(HERE / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(passed=report['passed'], templateCount=len(keys), serverCodesPreserved=True, multilingualAcceptance=False)))
if result.returncode:
    print(result.stdout + result.stderr)
raise SystemExit(0 if report['passed'] else 1)
