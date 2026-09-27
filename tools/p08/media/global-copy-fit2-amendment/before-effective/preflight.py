"""Verify current production source once per file with the active reviewed copy override."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys
import generate as active

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
UNITY = Path('C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/Managed/UnityEngine')
pointer = active.load(HERE / 'current.json')
plan_path = active.bound(pointer['active'])
plan = active.load(plan_path)
destination = active.file(pointer['outputDirectory'])


def snapshot():
    paths = set(HERE.glob('*.py')) | set(HERE.glob('*.csproj')) | set(HERE.glob('*.props')) | {HERE / 'current.json', plan_path}
    paths |= set((ROOT / 'Assets/RacingBois/Client').rglob('*.cs'))
    paths |= set(destination.glob('*.cs')) | set(destination.glob('*.csproj')) | {destination / 'changes.json', destination / 'authored-text-union.json'}
    paths |= set(UNITY.glob('*.dll'))
    for pattern in ['RacingBois.Client.Adapters.dll', 'RacingBois.Gameplay.Definitions.dll', 'RacingBois.Simulation.dll', 'RacingBois.Protocol.dll', 'RacingBois.NetworkMapping.dll', 'Unity.InputSystem.dll', 'Unity.RenderPipelines.*.dll']:
        paths |= set((ROOT / 'Library/ScriptAssemblies').glob(pattern))
    for row in [plan['baseUnion'], plan['authoredChanges']] + [module['base'] for module in plan['modules']] + [evidence for change in plan['changes'] for evidence in change['evidence']]:
        paths.add(active.bound(row))
    return {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


before = snapshot()
commands = []
calls = [[sys.executable, str(HERE / 'generate.py'), '--check'], [sys.executable, str(HERE / 'test_generation.py')],
         ['dotnet', 'run', '--project', str(destination / 'Checks.csproj'), '--nologo']]
calls += [['dotnet', 'build', str(HERE / 'BootstrapPreflight.csproj'), '--nologo', '-p:Flavor=' + flavor] for flavor in ['Editor', 'Windows', 'Web']]
for command in calls:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    commands.append({'command': command, 'exitCode': result.returncode, 'output': result.stdout + result.stderr})
    if result.returncode:
        raise RuntimeError(commands[-1]['output'])
if before != snapshot():
    raise RuntimeError('Current source/reference or reviewed copy input changed during checks')
receipt = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'passed': True, 'inputsStable': True,
           'scope': 'Current managed source compilation, effective copy generation/lookup and negative contracts; native rendering/readability acceptance remains separate.',
           'commands': commands, 'inputs': [{'path': str(Path(path).relative_to(ROOT)).replace('\\', '/') if ROOT in Path(path).parents else path.replace('\\', '/'), 'sha256': value} for path, value in before.items()],
           'nativeUiAccepted': False}
(destination / 'validation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({'passed': True, 'commands': len(commands), 'boundInputs': len(before), 'managedFlavors': 3, 'nativeUiAccepted': False}))
