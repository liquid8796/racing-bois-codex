"""Read-only diagnosis of iptables-save counter-sensitive hash evidence."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[3]
ssh=['ssh','-i','C:/Users/Liquid/.ssh/jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36']
code='''import datetime,hashlib,json,re,subprocess,time,urllib.request
def snapshot():
    result={}
    for command in ['iptables-save','ip6tables-save']:
        raw=subprocess.check_output([command],text=True)
        lines=[line for line in raw.splitlines() if not line.startswith('#')]
        plain='\\n'.join(lines);normalized=re.sub(r'\\[\\d+:\\d+\\]','[COUNTERS]',plain)
        result[command]={'rawHash':hashlib.sha256(plain.encode()).hexdigest(),'counterNormalizedHash':hashlib.sha256(normalized.encode()).hexdigest(),'chainCounters':re.findall(r'\\[\\d+:\\d+\\]',plain),'ruleLines':sum(line.startswith('-A ') for line in lines)}
    return result
before=snapshot()
with urllib.request.urlopen('https://racing-bois.158.180.59.36.sslip.io/ready',timeout=15) as response:status=response.status
time.sleep(2)
after=snapshot()
same=all(before[name]['counterNormalizedHash']==after[name]['counterNormalizedHash'] for name in before)
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed_read_only_counter_diagnosis' if same else 'failed_structural_change_detected','before':before,'after':after,'httpsStatus':status,'normalizedRulesIdenticalAcrossTheseReads':same,'preDeploymentNormalizedDigestRecorded':False,'scope':'Two post-deployment read-only snapshots around an ordinary HTTPS request. Establishes counter sensitivity, not an unavailable pre-deployment structural digest.'}))
'''
result=subprocess.run(ssh+['sudo -n python3 -'],input=code,text=True,capture_output=True,timeout=45)
if result.returncode:raise RuntimeError('Read-only firewall diagnosis failed; raw output suppressed')
report=json.loads(result.stdout)
(ROOT/'docs/p09/releases/e/firewall-counter-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'normalizedRulesIdenticalAcrossTheseReads':report['normalizedRulesIdenticalAcrossTheseReads'],'rawIpv4Changed':report['before']['iptables-save']['rawHash']!=report['after']['iptables-save']['rawHash'],'preDeploymentNormalizedDigestRecorded':False}))
if not report['normalizedRulesIdenticalAcrossTheseReads']:raise SystemExit(1)
