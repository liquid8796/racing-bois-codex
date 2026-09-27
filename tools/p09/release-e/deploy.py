"""Release-e orchestration over the exact authorized SSH route; safe receipts only."""
from pathlib import Path,PurePosixPath
import argparse,datetime,hashlib,io,json,re,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
RELEASE='p09-20260927-e';EXPECTED_SOURCE='90f38b173fcd7edac01a138d5aee5da1f4a773112f9ddf827e7ab1e045c54544'
EXPECTED_ARCHIVE='f26982d79b9b49f5e572d31490f97dcc85ad3a078d271b616c81ecb80c5434e5'
REPORT=ROOT/'docs/p09/releases/e';PRIVATE=ROOT/'_local/p09/release-e';REPORT.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True)
SSH=['ssh','-i','C:/Users/Liquid/.ssh/jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36']
SCP=['scp','-i','C:/Users/Liquid/.ssh/jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes']
def write(name,value):(REPORT/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def remote(command,stdin=None,timeout=120):
    result=subprocess.run(SSH+[command],input=stdin,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('Remote operation failed (exit '+str(result.returncode)+'); raw output suppressed')
    return result.stdout.strip()
def upload(source,destination,recursive=False):
    result=subprocess.run(SCP+(['-r'] if recursive else [])+[str(source),'ubuntu@158.180.59.36:'+destination],capture_output=True,text=True,timeout=240)
    if result.returncode:raise RuntimeError('Upload failed; raw output suppressed')
def state():return json.loads(remote('sudo -n python3 -', (HERE/'remote-state.py').read_text(),120))
def stage():
    value=json.loads((PRIVATE/'stage.json').read_text())['directory']
    if not re.fullmatch(r'/tmp/racing-bois-p09\.[A-Za-z0-9]+',value):raise RuntimeError('Invalid staging path')
    return value
def verify_local():
    archive=ROOT/'Build/OciStaging'/f'{RELEASE}.tar.gz';manifest=json.loads((ROOT/'Build/OciStaging'/RELEASE/'release.json').read_text())
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=EXPECTED_ARCHIVE or manifest['source']['sha256']!=EXPECTED_SOURCE:raise RuntimeError('Package identity mismatch')
    for group in ['source','testSource']:
        for entry in manifest[group]['files']:
            if hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:raise RuntimeError('Packaged source drift: '+entry['path'])
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            for value in [member.name]+([member.linkname] if member.islnk() or member.issym() else []):
                path=PurePosixPath(value)
                if path.is_absolute() or '..' in path.parts or '\\' in value or ':' in value:raise RuntimeError('Unsafe archive member')
            if member.issym():raise RuntimeError('Unexpected archive symlink')
    return archive,manifest
parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','test','activate','post']);args=parser.parse_args()
archive,manifest=verify_local()
if args.phase=='prepare':
    before=state();write('host-before.json',before);write('realm-before.json',before['realm'])
    if before['architecture']!='aarch64' or before['health']['multiplayer']['roomCount']!=0:raise RuntimeError('Unexpected architecture or active room during staging deployment')
    directory=remote('mktemp -d /tmp/racing-bois-p09.XXXXXXXX')
    if not re.fullmatch(r'/tmp/racing-bois-p09\.[A-Za-z0-9]+',directory):raise RuntimeError('Invalid stage creation output')
    (PRIVATE/'stage.json').write_text(json.dumps({'directory':directory}))
    print(json.dumps({'status':'UPLOADING','releaseId':RELEASE,'previous':before['releaseId']}),flush=True)
    upload(archive,directory+'/release.tar.gz');upload(ROOT/'tools/p09/infra',directory+'/ops',True)
    fixture=PRIVATE/'arm-fixtures.tar.gz';indexed={entry['path']:entry['sha256'] for entry in manifest['testSource']['files']}
    paths=list((ROOT/'Packages/com.racingbois.foundation/Runtime/Definitions').glob('*.cs'))+list((ROOT/'Packages/com.racingbois.foundation/Runtime/Simulation').glob('*.cs'))+[ROOT/'src/Tests/RacingBois.Gameplay.Tests/Program.cs']
    with tarfile.open(fixture,'w:gz') as tar:
        for path in paths:
            relative=path.relative_to(ROOT).as_posix()
            if hashlib.sha256(path.read_bytes()).hexdigest()!=indexed[relative]:raise RuntimeError('ARM source fixture drift')
            tar.add(path,arcname=relative)
    upload(fixture,directory+'/arm-fixtures.tar.gz')
    result=remote(f'sudo -n bash {directory}/ops/install.sh {RELEASE} {directory}/release.tar.gz {EXPECTED_ARCHIVE} {directory}/ops',timeout=180)
    safe=next(json.loads(line) for line in result.splitlines() if line.startswith('{'))
    if safe['sourceSha256']!=EXPECTED_SOURCE:raise RuntimeError('Installed source mismatch')
    write('installation.json',{'releaseId':RELEASE,'archiveSha256':EXPECTED_ARCHIVE,'nativeSourceFixtureSha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),**safe})
    print(json.dumps({'status':'PREPARED','releaseId':RELEASE,'files':safe['files']}))
elif args.phase=='test':
    directory=stage();qa='/var/lib/racing-bois-staging/qa/'+RELEASE
    remote(f'sudo -n install -d -m 0700 -o racing-bois-staging -g racing-bois-staging {qa}')
    remote(f'sudo -n tar -xzf {directory}/arm-fixtures.tar.gz -C {qa} --no-same-owner')
    remote(f'sudo -n chown -R racing-bois-staging:racing-bois-staging {qa}')
    summaries=[]
    for kind,binary in [('multiplayer','RacingBois.Multiplayer.Integration.Tests'),('gameplay','RacingBois.Gameplay.Tests'),('persistence','RacingBois.Persistence.Tests')]:
        output=qa+'/arm64-'+kind+'-e.json';argument=('--report ' if kind=='persistence' else '')+output
        remote(f'sudo -n systemd-run --wait --pipe --collect --quiet --unit=racing-bois-qa-e-{kind} --uid=racing-bois-staging --working-directory={qa} --property=CPUQuota=75% --property=MemoryMax=768M --property=RuntimeMaxSec=300 /srv/racing-bois/releases/{RELEASE}/tests/{kind}/{binary} {argument}',timeout=360)
        result=json.loads(remote(f'sudo -n -u racing-bois-staging cat {output}'))
        write('arm64-'+kind+'-e.json',result)
        failures=result.get('failed',result.get('failures',0))
        if failures or result.get('passed') is False:raise RuntimeError('ARM '+kind+' tests failed')
        count=result.get('tests',len(result.get('results',[])))
        if isinstance(count,list):count=len(count)
        summaries.append({'suite':kind,'report':'arm64-'+kind+'-e.json','passed':result.get('passed'),'tests':count,'failed':failures})
        print(json.dumps({'status':'ARM_SUITE_PASSED',**summaries[-1]}),flush=True)
    write('arm-validation.json',{'status':'passed','releaseId':RELEASE,'sourceSha256':EXPECTED_SOURCE,'testSourceSha256':manifest['testSource']['sha256'],'runtime':'linux-arm64','suites':summaries})
elif args.phase=='activate':
    arm=json.loads((REPORT/'arm-validation.json').read_text())
    if arm['status']!='passed' or arm['sourceSha256']!=EXPECTED_SOURCE:raise RuntimeError('Native acceptance does not match candidate')
    remote('sudo -n systemctl start racing-bois-backup')
    write('backup-before-activation.json',json.loads(remote('sudo -n cat /srv/racing-bois/backups/latest.json')))
    before=state();write('activation-host-before.json',before);write('realm-before.json',before['realm'])
    if before['health']['multiplayer']['roomCount']!=0:raise RuntimeError('Active room appeared before activation')
    result=json.loads(remote(f'sudo -n bash {stage()}/ops/activate.sh {RELEASE}',timeout=100));write('activation.json',result)
    after=state();write('host-after-activation.json',after);write('realm-after.json',after['realm'])
    preserved=before['realm']==after['realm']
    write('upgrade-data-check.json',{'status':'passed' if preserved else 'failed','releaseId':RELEASE,'entireLogicalRealmStatePreserved':preserved,'realmId':after['realm']['realmId'],'profileCount':after['realm']['profileCount'],'creditsTotal':after['realm']['creditsTotal']})
    if not preserved or after['releaseId']!=RELEASE or after['sourceSha256']!=EXPECTED_SOURCE:raise RuntimeError('Upgrade state/source verification failed')
    print(json.dumps({'status':'ACTIVATED','releaseId':RELEASE,'entireLogicalRealmStatePreserved':True}))
elif args.phase=='post':
    after=state();write('host-after.json',after);before=json.loads((REPORT/'host-before.json').read_text())
    shared={'caddyConfigSha256':before['caddyConfigSha256']==after['caddyConfigSha256'],
            'rawCounterSensitiveFirewallHashEqual':before['firewallRulesSha256']==after['firewallRulesSha256']}
    baseline=before.get('firewallCounterNormalizedSha256')
    shared['firewallRulesUnchanged']=None if baseline is None else baseline==after['firewallCounterNormalizedSha256']
    shared['firewallEvidence']='Pre-deployment counter-normalized baseline unavailable; retain original failed raw-hash receipt and separate counter diagnosis.' if baseline is None else 'Counter-normalized before/after rule hashes.'
    shared['existingSiteHttpStatus']=after['existingSiteHttpStatus'];shared['releaseId']=after['releaseId']
    shared['priorUnrelatedServicesStillRunning']=all(name in after['runningServices'] for name in before['runningServices'] if not name.startswith('racing-bois-'))
    other_passed=shared['caddyConfigSha256'] and shared['priorUnrelatedServicesStillRunning'] and shared['existingSiteHttpStatus']==before['existingSiteHttpStatus']
    shared['status']='inconclusive_firewall_baseline' if baseline is None and other_passed else 'passed' if other_passed and shared['firewallRulesUnchanged'] else 'failed'
    write('shared-services-postcheck.json',shared)
    verified=json.loads(remote(f'sudo -n python3 {stage()}/ops/verify-deployment.py'));write('deployment-verification.json',verified)
    if shared['status']!='passed' or verified['releaseId']!=RELEASE or verified['sourceSha256']!=EXPECTED_SOURCE:raise RuntimeError('Postcheck failed')
    print(json.dumps({'status':'POSTCHECK_PASSED','releaseId':RELEASE,'verifiedFiles':verified['verifiedFiles'],'sharedServicesPreserved':True}))
