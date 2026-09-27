"""Supervise a source-bound public WSS soak and private OCI observations, then write its own release receipt."""
from __future__ import annotations
import argparse,datetime,json,pathlib,re,subprocess,sys,time

ROOT=pathlib.Path(__file__).resolve().parents[2]
SSH=['ssh','-i',r'C:\Users\Liquid\.ssh\jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36']
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--release',required=True);parser.add_argument('--output',required=True);parser.add_argument('--seconds',type=int,default=1800)
args=parser.parse_args()
if not re.fullmatch('[a-z0-9-]{1,48}',args.release) or not 30<=args.seconds<=28800:raise ValueError('Invalid release or bounded duration')
output=(ROOT/args.output).resolve()
if not output.is_relative_to(ROOT/'docs/p09'):raise ValueError('Release evidence must remain under docs/p09')
output.mkdir(parents=True,exist_ok=True)
private=ROOT/'_local/p09'/('wan-'+args.release);private.mkdir(parents=True,exist_ok=False)
status_path=output/'wan-supervisor.json'
def write(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2));temporary.replace(path)
def remote(command):
    result=subprocess.run(SSH+[command],capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError('SSH verification failed')
    return json.loads(result.stdout)
def relative(path):return path.relative_to(ROOT).as_posix()
record={'schemaVersion':1,'status':'PREPARING','releaseId':args.release,'startedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':args.seconds,'scope':'One Windows-origin eight-peer WSS room to OCI; rendered Unity and worldwide gameplay acceptance remain separate.'}
write(status_path,record)
network=None;observer=None
try:
    deployed=remote('cat /srv/racing-bois/current/release.json')
    if deployed['releaseId']!=args.release:raise RuntimeError('Unexpected active release')
    record['sourceSha256']=deployed['source']['sha256']
    write(output/'network-health-before.json',remote('curl --fail --silent http://127.0.0.1:18080/health'))
    with (private/'network.stdout.log').open('w') as stdout,(private/'network.stderr.log').open('w') as stderr,(private/'observer.stdout.log').open('w') as obsout,(private/'observer.stderr.log').open('w') as obserr:
        network=subprocess.Popen([sys.executable,'-u','tools/p10/run-network-diagnostic.py','--endpoint','wss://racing-bois.158.180.59.36.sslip.io/multiplayer',
                                  '--health-url','https://racing-bois.158.180.59.36.sslip.io/ready','--seconds',str(args.seconds),'--peers','8'],cwd=ROOT,stdout=stdout,stderr=stderr,creationflags=0x08000000)
        deadline=time.monotonic()+90;launch=None
        while time.monotonic()<deadline and network.poll() is None:
            for line in (private/'network.stdout.log').read_text().splitlines():
                try:candidate=json.loads(line)
                except json.JSONDecodeError:continue
                if candidate.get('status')=='RUNNING':launch=candidate;break
            if launch:break
            time.sleep(1)
        if not launch or not re.fullmatch(r'\d{8}T\d{6}Z',launch['runId']):raise RuntimeError('Network harness did not start')
        run=ROOT/'docs/p10/network'/launch['runId']/'run.json'
        observer=subprocess.Popen([sys.executable,'-u','tools/p09/observe-soak.py',relative(run),relative(output/'soak-observer.json')],cwd=ROOT,stdout=obsout,stderr=obserr,creationflags=0x08000000)
        record.update(status='RUNNING',networkRunId=launch['runId'],networkReceipt=relative(run),networkSupervisorPid=network.pid,probePid=launch.get('probePid'),observerPid=observer.pid)
        write(status_path,record);print(json.dumps(record),flush=True)
        code=network.wait(timeout=args.seconds+180)
        observer.wait(timeout=60)
        write(output/'network-health-after.json',remote('curl --fail --silent http://127.0.0.1:18080/health'))
        deployed_after=remote('sudo -n python3 /srv/racing-bois/ops/verify-deployment.py')
        write(output/'deployment-after-soak.json',deployed_after)
        if code or deployed_after['releaseId']!=args.release or deployed_after['sourceSha256']!=record['sourceSha256']:raise RuntimeError('Network or deployed source changed/failed')
        finalized=subprocess.run([sys.executable,'tools/p09/finalize-report.py','--release',args.release,'--network-run',launch['runId'],
          '--before',relative(output/'network-health-before.json'),'--after',relative(output/'network-health-after.json'),
          '--observer',relative(output/'soak-observer.json'),'--output',relative(output/'capacity.json')],cwd=ROOT,capture_output=True,text=True,timeout=30)
        if finalized.returncode:raise RuntimeError('Capacity evidence did not pass')
        record.update(status='PASS',finishedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),capacityReceipt=relative(output/'capacity.json'))
except Exception as error:
    record.update(status='FAIL',finishedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),errorType=type(error).__name__)
    # Only this supervisor's own children can be stopped, never an existing local/remote host.
    if network is not None and network.poll() is None:network.terminate()
    if observer is not None and observer.poll() is None:observer.terminate()
    write(status_path,record);print(json.dumps(record),flush=True);raise
write(status_path,record);print(json.dumps(record),flush=True)
