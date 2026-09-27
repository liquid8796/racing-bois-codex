"""Compile the staged authoring assembly and run scoped receipt controls without Unity."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
UNITY = Path('C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/Managed')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    paths = set(HERE.glob('*.cs')) | set(HERE.glob('*.csproj')) | set(HERE.glob('*.props')) | set(HERE.glob('*.py'))
    paths |= set((HERE / 'CompileAudit').glob('*.cs')) | set((HERE / 'CompileAudit').glob('*.csproj'))
    paths |= set((ROOT / 'Assets/RacingBois/Editor').rglob('*.cs'))
    paths.discard(ROOT / 'Assets/RacingBois/Editor/P08DesktopBuilder.cs')
    paths |= set((UNITY / 'UnityEngine').glob('*.dll')) | set((UNITY / 'UnityEditor').glob('*.dll'))
    for pattern in ['RacingBois.Client.*.dll', 'RacingBois.Gameplay.Definitions.dll', 'RacingBois.Protocol.dll', 'RacingBois.Simulation.dll', 'RacingBois.NetworkMapping.dll', 'RacingBois.Golden.dll', 'Unity.Collections.dll', 'Unity.InputSystem.dll', 'Unity.RenderPipelines.*.dll']:
        paths |= set((ROOT / 'Library/ScriptAssemblies').glob(pattern))
    paths.add(ROOT / 'Library/PackageCache/com.unity.nuget.newtonsoft-json@4dfd81071c64/Runtime/Newtonsoft.Json.dll')
    paths |= {ROOT / 'tools/p08/desktop/test_audit_desktop.py', ROOT / 'tools/p08/desktop/test_dependency_receipt.py', ROOT / 'tools/p08/content-pack/audit_publish.py'}
    return {str(path.resolve()): sha(path) for path in sorted(paths)}


before = inputs()
commands = []
for project in ['Preflight.csproj', 'CompileAudit/CompileAudit.csproj']:
    command = ['dotnet', 'build', str(HERE / project), '--nologo']
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    commands.append({'command': 'dotnet build tools/p08/desktop/safe-build-staging/' + project + ' --nologo', 'exitCode': result.returncode, 'output': result.stdout + result.stderr})
    if result.returncode:
        raise RuntimeError(commands[-1]['output'])
spec = importlib.util.spec_from_file_location('audit_desktop', HERE / 'audit_desktop.py')
candidate = importlib.util.module_from_spec(spec); sys.modules['audit_desktop'] = candidate; spec.loader.exec_module(candidate)
suite = unittest.TestSuite()
for name, path in [('historical_distribution', ROOT / 'tools/p08/desktop/test_audit_desktop.py'), ('historical_dependencies', ROOT / 'tools/p08/desktop/test_dependency_receipt.py'), ('scoped_receipts', HERE / 'test_scoped_receipt.py')]:
    spec = importlib.util.spec_from_file_location(name, path); tests = importlib.util.module_from_spec(spec); spec.loader.exec_module(tests)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(tests))
result = unittest.TextTestRunner(verbosity=1).run(suite)
after = inputs()
if before != after or not result.wasSuccessful():
    raise RuntimeError('Source/reference drift or failing contract test')
rows = []
for path, value in before.items():
    logical = str(Path(path).relative_to(ROOT)).replace('\\', '/') if ROOT in Path(path).parents else path.replace('\\', '/')
    rows.append({'path': logical, 'sha256': value})
receipt = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'passed': True, 'inputsStable': True,
           'scope': 'Staged managed compilation and synthetic file/receipt contracts. No Unity build, font/scene restoration, runtime or release acceptance inferred.',
           'testsRun': result.testsRun, 'commands': commands, 'inputs': rows, 'nativeBuildVerified': False, 'releaseAccepted': False}
(HERE / 'validation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({'passed': True, 'testsRun': result.testsRun, 'boundInputs': len(rows), 'managedBuilds': len(commands), 'nativeBuildVerified': False}))
