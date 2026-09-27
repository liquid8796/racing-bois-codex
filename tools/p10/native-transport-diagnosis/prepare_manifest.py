"""Bind the one transport change and its permanent behavioral regression for review."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
manifest=json.loads((HERE/'transport-manifest.json').read_text())
program=(HERE/'TransportTestProgram.cs').read_text(encoding='utf8')
program=program.replace('tools/p10/native-transport-diagnosis/Transport/BrowserSocketTransport.cs','Assets/RacingBois/Client/Adapters/BrowserSocketTransport.cs')
program=program.replace('tools/p10/native-transport-diagnosis/TransportTestProgram.cs','src/Tests/RacingBois.NativeTransport.Tests/Program.cs')
program=program.replace('tools/p10/native-transport-diagnosis/TransportTests.csproj','src/Tests/RacingBois.NativeTransport.Tests/RacingBois.NativeTransport.Tests.csproj')
program=program.replace('Staged native BrowserSocketTransport','Actual linked native BrowserSocketTransport')
staged=HERE/'Transport/NativeTransportTestProgram.cs';staged.write_text(program,encoding='utf8')
path='src/Tests/RacingBois.NativeTransport.Tests/Program.cs'
manifest['changes'].append({'path':path,'before':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'staged':staged.relative_to(ROOT).as_posix(),'after':hashlib.sha256(staged.read_bytes()).hexdigest()})
(HERE/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print(hashlib.sha256((HERE/'candidate-manifest.json').read_bytes()).hexdigest())
