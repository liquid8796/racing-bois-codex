"""Publish and run a new loopback-only server/realm and diagnostic observer."""
from pathlib import Path
import argparse,datetime,hashlib,json,socket,subprocess,sys,time,urllib.request

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory():
    paths=[]
    for folder in ['src','Packages/com.racingbois.foundation/Runtime','Assets/RacingBois/Client/Application','tools/p10/ProtocolSoak','tools/p10/ProtocolSoakNext','tools/p10/correction-audit']:
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ['.cs','.csproj','.props','.targets'] and not {'bin','obj'}.intersection(p.parts))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
def write(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8');temp.replace(path)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=180);args=parser.parse_args()
    if not 30<=args.seconds<=1800:parser.error('seconds must be30..1800')
    run=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output=ROOT/'docs/p10/correction-audit'/run;output.mkdir(parents=True,exist_ok=False)
    private=ROOT/'_local/p10/correction-audit'/run;private.mkdir(parents=True,exist_ok=False)
    before=inventory();record={'schema':1,'runId':run,'status':'PREPARING','sourceBefore':before,'seconds':args.seconds,'peers':8,'realm':'New isolated loopback offline realm','recipeSha256':sha(Path(__file__))}
    server=None;probe=None;handles=[];receipt=output/'run.json';write(receipt,record)
    flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
    try:
        for label,project in [('server','src/Server/RacingBois.Server.Host'),('probe','tools/p10/correction-audit/CorrectionAudit.csproj')]:
            with (private/(label+'-build.log')).open('wb') as log:
                result=subprocess.run(['dotnet','publish',project,'-c','Release','--no-self-contained','-o',str(private/label),'--nologo'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=flags)
            if result.returncode:raise RuntimeError(label+'_build_failed')
        if inventory()!=before:raise RuntimeError('source_changed_during_build')
        with socket.socket() as reserved:reserved.bind(('127.0.0.1',0));port=reserved.getsockname()[1]
        public=private/'empty-public';public.mkdir()
        log=(private/'server.log').open('wb');handles.append(log)
        server=subprocess.Popen(['dotnet',str(private/'server/RacingBois.Server.Host.dll'),'--Port',str(port),'--AllowLan','false','--EnableTls','false','--RealmKind','offline','--DataRoot',str(private/'private-realm'),'--WebRoot',str(public),'--Logging:LogLevel:Default','Warning'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        record.update(serverPid=server.pid,port=port)
        for _ in range(100):
            if server.poll() is not None:raise RuntimeError('owned_server_start_failed')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/ready',timeout=1) as response:
                    if response.status==200:break
            except Exception:time.sleep(.1)
        else:raise RuntimeError('owned_server_readiness_timeout')
        log=(private/'probe.log').open('wb');handles.append(log)
        probe=subprocess.Popen(['dotnet',str(private/'probe/CorrectionAudit.dll'),f'ws://127.0.0.1:{port}/multiplayer',str(output/'probe.json'),str(args.seconds),'8'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        record.update(status='RUNNING',probePid=probe.pid);write(receipt,record)
        print(json.dumps({'runId':run,'serverPid':server.pid,'probePid':probe.pid,'port':port,'receipt':str(receipt)}),flush=True)
        began=time.monotonic()
        while probe.poll() is None:
            if time.monotonic()-began>args.seconds+120:raise RuntimeError('owned_probe_wall_timeout')
            time.sleep(1)
        data=json.loads((output/'probe.json').read_text(encoding='utf8'))
        record.update(status='PASS' if probe.returncode==0 and data.get('status')=='PASS' else 'FAIL',probeExitCode=probe.returncode,probeSha256=sha(output/'probe.json'),maximumCorrection=data.get('correctionTrace',{}).get('maximumCorrection'))
    except Exception as error:record.update(status='FAIL',errorCode=str(error))
    finally:
        # Only process handles created above are owned; no existing PID/name lookup.
        for process,label in [(probe,'ownedProbe'),(server,'ownedServer')]:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
                record[label+'ExitCode']=process.returncode
        for handle in handles:handle.close()
        after=inventory();record['changedSources']=[p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)];record['sourceStable']=not record['changedSources']
        if record['changedSources']:record['status']='SUPERSEDED'
        write(receipt,record)
    print(json.dumps({k:record.get(k) for k in ['runId','status','errorCode','maximumCorrection','sourceStable']}),flush=True)
    return 0 if record['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
