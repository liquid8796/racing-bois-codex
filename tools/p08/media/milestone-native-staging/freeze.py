"""Record the helper/source/reference identities after its ordinary managed build."""
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[3]
output = here / 'bin/NativeContracts/Debug/netstandard2.1/RacingBois.Tools.NativeMilestoneContracts.dll'
managed = Path('C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/Managed/UnityEngine')
def record(path):
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

payload = {'schema': 1, 'helper': record(output), 'sources': [record(here / name) for name in
    ('NativeContracts.cs', 'Fixtures.cs', 'NativeContracts.csproj', 'Directory.Build.props')],
    'compileReferences': [record(root / 'Library/ScriptAssemblies' / (name + '.dll')) for name in
    ('RacingBois.Client.Application', 'RacingBois.Client.Adapters', 'RacingBois.Protocol', 'RacingBois.Gameplay.Definitions')],
    'unityCore': record(managed / 'UnityEngine.CoreModule.dll'),
    'json': record(root / 'Library/PackageCache/com.unity.nuget.newtonsoft-json@4dfd81071c64/Runtime/Newtonsoft.Json.dll'),
    'linkedProductionSources': False, 'nativeExecution': False, 'fullCampaignAccepted': False}
(here / 'handoff.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'helperSha256': payload['helper']['sha256'], 'sourceFiles': len(payload['sources']), 'nativeExecution': False}))
