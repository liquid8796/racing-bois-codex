"""Approved f preparation and capped ARM QA only; this tool cannot activate a release."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,re,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
RELEASE='p09-20260927-f';EXPECTED_SOURCE='194d60c159d8978a8520d17df1c900cae09e2614d4b1f620c89b9a5bbcf54c24'
EXPECTED_ARCHIVE='3eeae66746ba7de5293a3d76b833eb0c930dc3f09bd4388d3e08da2bf9d68ca9'
EXPECTED_FIXTURE='14801052aea2ba8fab8446f5000228dbb303c4b11575c0b7ec74711e49693d10'
REPORT=ROOT/'docs/p09/releases/f';PRIVATE=ROOT/'_local/p09/release-f';PRIVATE.mkdir(parents=True,exist_ok=True)
SSH=['ssh','-i','C:/Users/Liquid/.ssh/jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36']
SCP=['scp','-i','C:/Users/Liquid/.ssh/jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes']
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(name,value):
    path=REPORT/name
    if path.exists():raise RuntimeError('Immutable receipt already exists: '+name)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
def remote(command,stdin=None,timeout=120):
    result=subprocess.run(SSH+[command],input=stdin,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('Remote operation failed (exit '+str(result.returncode)+'); raw output suppressed')
    return result.stdout.strip()
def upload(source,destination,recursive=False):
    result=subprocess.run(SCP+(['-r'] if recursive else [])+[str(source),'ubuntu@158.180.59.36:'+destination],capture_output=True,text=True,timeout=300)
    if result.returncode:raise RuntimeError('Scoped upload failed; raw output suppressed')
def state():return json.loads(remote('sudo -n python3 -',(ROOT/'tools/p09/release-e/remote-state.py').read_text(),120))
def stage():
    value=json.loads((PRIVATE/'stage.json').read_text())['directory']
    if not re.fullmatch(r'/tmp/racing-bois-p09\.[A-Za-z0-9]+',value):raise RuntimeError('Invalid owned staging directory')
    return value
def verify_local():
    archive=ROOT/'Build/OciStaging'/f'{RELEASE}.tar.gz';fixture=ROOT/'Build/OciStaging'/f'{RELEASE}-arm-fixtures.tar.gz'
    manifest=json.loads((ROOT/'Build/OciStaging'/RELEASE/'release.json').read_text())
    if digest(archive)!=EXPECTED_ARCHIVE or digest(fixture)!=EXPECTED_FIXTURE or manifest['source']['sha256']!=EXPECTED_SOURCE:raise RuntimeError('Package identity mismatch')
    for group in ['source','testSource']:
        for row in manifest[group]['files']:
            if digest(ROOT/row['path'])!=row['sha256']:raise RuntimeError('Packaged source drift: '+row['path'])
    for path in [archive,fixture]:
        with tarfile.open(path) as tar:
            for member in tar.getmembers():
                for name in [member.name]+([member.linkname] if member.islnk() else []):
                    p=PurePosixPath(name)
                    if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:raise RuntimeError('Unsafe archive path')
                if member.issym():raise RuntimeError('Unexpected archive symlink')
    return archive,fixture,manifest
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','test','post-prepare']);args=parser.parse_args()
archive,fixture,manifest=verify_local()
if args.phase=='prepare':
    before=state();write('host-before-prepare.json',before)
    if before['architecture']!='aarch64' or before['releaseId']!='p09-20260927-e' or before['health']['multiplayer']['roomCount']!=0:raise RuntimeError('Unexpected active release/architecture or active room')
    directory=remote('mktemp -d /tmp/racing-bois-p09.XXXXXXXX')
    if not re.fullmatch(r'/tmp/racing-bois-p09\.[A-Za-z0-9]+',directory):raise RuntimeError('Unexpected stage creation result')
    (PRIVATE/'stage.json').write_text(json.dumps({'directory':directory}),encoding='utf8')
    print(json.dumps({'status':'UPLOADING','releaseId':RELEASE,'activeRemains':before['releaseId']}),flush=True)
    upload(archive,directory+'/release.tar.gz');upload(fixture,directory+'/arm-fixtures.tar.gz');upload(ROOT/'tools/p09/infra',directory+'/ops',True)
    actual=remote('sha256sum '+directory+'/release.tar.gz '+directory+'/arm-fixtures.tar.gz')
    lines=actual.splitlines()
    if len(lines)!=2 or lines[0].split()[0]!=EXPECTED_ARCHIVE or lines[1].split()[0]!=EXPECTED_FIXTURE:raise RuntimeError('Uploaded archive hash mismatch')
    result=remote(f'sudo -n bash {directory}/ops/install.sh {RELEASE} {directory}/release.tar.gz {EXPECTED_ARCHIVE} {directory}/ops',timeout=180)
    safe=next(json.loads(line) for line in result.splitlines() if line.startswith('{'))
    if safe['sourceSha256']!=EXPECTED_SOURCE:raise RuntimeError('Installed source mismatch')
    additional=['prediction/RacingBois.Prediction.Tests','prediction-projection/RacingBois.PredictionProjection.Tests','p05-client/RacingBois.P05Client.Tests']
    remote('sudo -n chmod 0755 '+' '.join('/srv/racing-bois/releases/'+RELEASE+'/tests/'+name for name in additional))
    if remote('readlink -f /srv/racing-bois/current')!='/srv/racing-bois/releases/p09-20260927-e':raise RuntimeError('Active release changed unexpectedly')
    write('installation.json',{'releaseId':RELEASE,'archiveSha256':EXPECTED_ARCHIVE,'nativeSourceFixtureSha256':EXPECTED_FIXTURE,'activeReleaseUnchanged':'p09-20260927-e',**safe})
    print(json.dumps({'status':'PREPARED','releaseId':RELEASE,'files':safe['files'],'activeRemains':'p09-20260927-e'}),flush=True)
elif args.phase=='test':
    directory=stage();qa='/var/lib/racing-bois-staging/qa/'+RELEASE
    remote(f'sudo -n test ! -e {qa}')
    remote(f'sudo -n install -d -m 0700 -o racing-bois-staging -g racing-bois-staging {qa}')
    remote(f'sudo -n tar -xzf {directory}/arm-fixtures.tar.gz -C {qa} --no-same-owner')
    remote(f'sudo -n chown -R racing-bois-staging:racing-bois-staging {qa}')
    summaries=[]
    suites=[('multiplayer','RacingBois.Multiplayer.Integration.Tests',32),('gameplay','RacingBois.Gameplay.Tests',31),('persistence','RacingBois.Persistence.Tests',26),
            ('prediction','RacingBois.Prediction.Tests',13),('prediction-projection','RacingBois.PredictionProjection.Tests',10),('p05-client','RacingBois.P05Client.Tests',36)]
    for kind,binary,expected in suites:
        output=qa+'/arm64-'+kind+'-f.json';argument=('--report ' if kind=='persistence' else '')+output
        remote(f'sudo -n systemd-run --wait --pipe --collect --quiet --unit=racing-bois-qa-f-{kind} --uid=racing-bois-staging --working-directory={qa} --property=CPUQuota=75% --property=MemoryMax=768M --property=RuntimeMaxSec=300 /srv/racing-bois/releases/{RELEASE}/tests/{kind}/{binary} {argument}',timeout=360)
        result=json.loads(remote(f'sudo -n -u racing-bois-staging cat {output}'));write('arm64-'+kind+'-f.json',result)
        failures=result.get('failed',result.get('failures',0));count=result.get('tests',len(result.get('results',[])))
        if isinstance(count,list):count=len(count)
        if failures or result.get('passed') is False or count!=expected:raise RuntimeError('ARM suite failed or group count changed: '+kind)
        indexed={row['path']:row['sha256'] for row in manifest['testSource']['files']}
        for row in result.get('sources',[]):
            if indexed.get(row['path'])!=row['sha256']:raise RuntimeError('ARM receipt source differs: '+row['path'])
        item={'suite':kind,'report':'arm64-'+kind+'-f.json','passed':True,'tests':count,'failed':failures};summaries.append(item);print(json.dumps({'status':'ARM_SUITE_PASSED',**item}),flush=True)
    write('arm-validation.json',{'status':'passed','releaseId':RELEASE,'sourceSha256':EXPECTED_SOURCE,'testSourceSha256':manifest['testSource']['sha256'],'runtime':'linux-arm64','totalGroups':sum(row['tests'] for row in summaries),'suites':summaries})
elif args.phase=='post-prepare':
    before=json.loads((REPORT/'host-before-prepare.json').read_text());after=state();write('host-after-prepare.json',after)
    checks={'activeReleaseStillE':after['releaseId']=='p09-20260927-e','activeSourceUnchanged':after['sourceSha256']==before['sourceSha256'],
            'realmStatePreserved':after['realm']==before['realm'],'caddyFilesUnchanged':after['caddyConfigSha256']==before['caddyConfigSha256'],
            'normalizedFirewallUnchanged':after['firewallCounterNormalizedSha256']==before['firewallCounterNormalizedSha256'],
            'unrelatedServicesStillRunning':all(name in after['runningServices'] for name in before['runningServices'] if not name.startswith('racing-bois-')),
            'unrelatedSiteStatusPreserved':after['existingSiteHttpStatus']==before['existingSiteHttpStatus']==200}
    write('prepare-postcheck.json',{'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'scope':'Preparation/ARMQA only; e still active. No activation, Caddy/firewall edit or unrelated service restart.'})
    if not all(checks.values()):raise RuntimeError('Preparation postcheck failed')
    print(json.dumps({'status':'PREPARE_POSTCHECK_PASS','activeRemains':after['releaseId']}))
