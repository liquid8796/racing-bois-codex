"""Actual installed Unity Mono transport source with an isolated frame context and owned echo server."""
from pathlib import Path
import datetime as dt,json,subprocess,time,sys,hashlib
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
mono=Path('C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/MonoBleedingEdge')
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=ROOT/'docs/p10/native-transport-diagnosis'/('mono-frames-'+stamp);out.mkdir(parents=True,exist_ok=False)
private=ROOT/'_local/p10/native-transport-diagnosis'/stamp;private.mkdir(parents=True,exist_ok=False)
exe=private/'MonoFrames.exe'
transport=HERE/'Transport/BrowserSocketTransport.cs' if '--candidate' in sys.argv else ROOT/'Assets/RacingBois/Client/Adapters/BrowserSocketTransport.cs'
command=[str(mono/'bin/mono.exe'),str(mono/'lib/mono/4.5/csc.exe'),'/nologo','/out:'+str(exe),'/r:'+str(mono/'lib/mono/4.8-api/System.dll'),'/r:'+str(mono/'lib/mono/4.8-api/System.Core.dll'),
         str(HERE/'MonoFrames.cs'),str(transport),str(ROOT/'src/Tests/RacingBois.NativeTransport.Tests/UnityShell.cs')]
subprocess.run(command,cwd=ROOT,check=True)
subprocess.run(['dotnet','build',str(HERE/'EchoHost/EchoHost.csproj'),'-c','Release','-v:q'],cwd=ROOT,check=True)
address=private/'endpoint.txt';log=(private/'echo.log').open('wb');server=subprocess.Popen(['dotnet',str(HERE/'EchoHost/bin/Release/net10.0/EchoHost.dll'),str(address)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    for _ in range(100):
        if address.exists():break
        if server.poll() is not None:raise RuntimeError('Owned echo host exited')
        time.sleep(.1)
    endpoint=address.read_text();results=[]
    for mode in ['none','frame']:
        report=out/(mode+'.json');run=subprocess.run([str(mono/'bin/mono.exe'),str(exe),endpoint,mode,str(report)],cwd=ROOT,timeout=40,capture_output=True,text=True)
        if not report.exists():raise RuntimeError('Mono failed: '+run.stdout[:500]+run.stderr[:500])
        value=json.loads(report.read_text());value['exitCode']=run.returncode;results.append(value);print(json.dumps(value),flush=True)
    (out/'receipt.json').write_text(json.dumps({'scope':'Actual installed Unity Mono6.13 console runtime and source-bound transport, real loopback WebSocket echo, simulated frame SynchronizationContext. Not the Unity player, WAN/TLS or game acceptance.',
       'candidate':'--candidate' in sys.argv,'transportPath':transport.relative_to(ROOT).as_posix(),'transportSha256':hashlib.sha256(transport.read_bytes()).hexdigest(),'ownedServerPid':server.pid,'results':results},indent=2)+'\n')
finally:
    server.terminate();server.wait(timeout=10);log.close()
