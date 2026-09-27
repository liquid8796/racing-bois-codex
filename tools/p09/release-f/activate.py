"""Root-authorized f activation after the completed local30m gate; scoped backup/lock/postchecks."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[3];REPORT=ROOT/'docs/p09/releases/f'
RELEASE='p09-20260927-f';SOURCE='194d60c159d8978a8520d17df1c900cae09e2614d4b1f620c89b9a5bbcf54c24'
SSH=['ssh','-i','C:/Users/Liquid/.ssh/jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36']
def remote(command,stdin=None,timeout=120):
    result=subprocess.run(SSH+[command],input=stdin,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('Scoped remote operation failed (exit '+str(result.returncode)+'); raw output suppressed')
    return result.stdout.strip()
def write(name,value):
    path=REPORT/name
    if path.exists():raise RuntimeError('Immutable activation receipt already exists: '+name)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
def state():return json.loads(remote('sudo -n python3 -',(ROOT/'tools/p09/release-e/remote-state.py').read_text(),120))
run=json.loads((ROOT/'docs/p10/network/20260926T230400Z/run.json').read_text())
probe=json.loads((ROOT/'docs/p10/network/20260926T230400Z/probe.json').read_text())
if run['status']!='PASS' or not run['sourceStable'] or probe['status']!='PASS' or not probe['sourceStable'] or probe['elapsedSeconds']<1800:raise SystemExit('Completed source-stable30-minute protocol/operations gate required. No activation.')
arm=json.loads((REPORT/'arm-validation.json').read_text())
if arm['status']!='passed' or arm['totalGroups']!=148 or arm['sourceSha256']!=SOURCE:raise SystemExit('Matching148-group native ARM acceptance required.')
manifest=json.loads((ROOT/'Build/OciStaging'/RELEASE/'release.json').read_text())
for row in manifest['source']['files']:
    if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise SystemExit('Backend source changed; do not activate.')
directory=json.loads((ROOT/'_local/p09/release-f/stage.json').read_text())['directory']
if not re.fullmatch(r'/tmp/racing-bois-p09\.[A-Za-z0-9]+',directory):raise SystemExit('Invalid owned stage directory.')
before_backup=state();write('host-before-backup.json',before_backup)
if before_backup['releaseId']!='p09-20260927-e' or before_backup['health']['multiplayer']['roomCount']!=0:raise SystemExit('Unexpected previous release or active room; no activation.')
remote('sudo -n systemctl start racing-bois-backup',timeout=120)
write('backup-before-activation.json',json.loads(remote('sudo -n cat /srv/racing-bois/backups/latest.json')))
before=state();write('activation-host-before.json',before)
if before['releaseId']!='p09-20260927-e' or before['health']['multiplayer']['roomCount']!=0:raise SystemExit('Active room/release changed after backup; no activation.')
result=json.loads(remote(f'sudo -n bash {directory}/ops/activate.sh {RELEASE}',timeout=100));write('activation.json',result)
after=state();write('host-after-activation.json',after)
checks={'correctRelease':after['releaseId']==RELEASE,'correctRuntimeSource':after['sourceSha256']==SOURCE,'protocol6':after['health']['multiplayer']['protocolVersion']==6,
        'entireLogicalRealmStatePreserved':before['realm']==after['realm'],'caddyFilesUnchanged':before['caddyConfigSha256']==after['caddyConfigSha256'],
        'normalizedFirewallUnchanged':before['firewallCounterNormalizedSha256']==after['firewallCounterNormalizedSha256'],
        'priorUnrelatedServicesStillRunning':all(name in after['runningServices'] for name in before['runningServices'] if not name.startswith('racing-bois-')),
        'unrelatedSiteStatusPreserved':before['existingSiteHttpStatus']==after['existingSiteHttpStatus']==200}
write('activation-postcheck.json',{'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'scope':'Backend staging activation only. Raw prediction/presentation outliers remain unaccepted; this is not visual, full Unity or eight-hour acceptance.'})
verified=json.loads(remote(f'sudo -n python3 {directory}/ops/verify-deployment.py'));write('deployment-verification.json',verified)
if not all(checks.values()) or verified['releaseId']!=RELEASE or verified['sourceSha256']!=SOURCE:raise RuntimeError('Post-activation verification failed; preserve evidence and report to root.')
print(json.dumps({'status':'ACTIVATED_AND_VERIFIED','releaseId':RELEASE,'protocolVersion':6,'verifiedFiles':verified['verifiedFiles'],'logicalRealmPreserved':True,'previousRetained':'p09-20260927-e'}),flush=True)
