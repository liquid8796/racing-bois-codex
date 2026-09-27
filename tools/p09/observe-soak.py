"""Record private server counters during a separately supervised WSS soak."""
import datetime,json,pathlib,subprocess,sys,time
root=pathlib.Path(__file__).resolve().parents[2];run=(root/sys.argv[1]).resolve()
if not run.is_relative_to(root/'docs/p10/network'):raise ValueError('Expected a source-bound P10 network receipt')
out=root/(sys.argv[2] if len(sys.argv)>2 else 'docs/p09/soak-observer.json');out.parent.mkdir(parents=True,exist_ok=True);samples=[]
ssh=['ssh','-i',r'C:\Users\Liquid\.ssh\jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36']
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
while True:
    state=json.loads(run.read_text())
    result=subprocess.run(ssh+["curl --fail --silent http://127.0.0.1:18080/health; printf '\\n'; sudo -n systemctl show racing-bois-staging -p MemoryCurrent -p CPUUsageNSec -p NRestarts -p MainPID"],capture_output=True,text=True,timeout=20)
    sample={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sshSucceeded':result.returncode==0}
    if result.returncode==0:
        lines=result.stdout.splitlines();sample['health']=json.loads(lines[0]);sample['service']={key:int(value) for line in lines[1:] if '=' in line for key,value in [line.split('=',1)]}
    samples.append(sample)
    report={'schemaVersion':1,'startedUtc':started,'networkRun':str(run.relative_to(root)),'networkStatus':state['status'],'samplingSeconds':30,'samples':samples,
            'scope':'Private counters and cgroup resources sampled after the soak began; start/end timestamps define observed coverage.'}
    temp=out.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2));temp.replace(out)
    if state['status']!='RUNNING':break
    time.sleep(30)
print(json.dumps({'status':'recorded','samples':len(samples),'networkStatus':state['status']}))
