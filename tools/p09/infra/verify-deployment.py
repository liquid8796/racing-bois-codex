#!/usr/bin/env python3
"""Safe deployment receipt: validate immutable bytes, Unix privacy and resource limits without reading secrets."""
import datetime,hashlib,json,os,pathlib,platform,stat,subprocess,urllib.request
root=pathlib.Path('/srv/racing-bois');current=(root/'current').resolve()
if current.parent!=root/'releases':raise RuntimeError('Invalid active release target')
manifest=json.loads((current/'release.json').read_text());bad=[]
for entry in manifest['files']:
    path=(current/entry['path']).resolve()
    if not path.is_relative_to(current) or not path.is_file():raise RuntimeError('Invalid release member')
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=entry['sha256'] or path.stat().st_size!=entry['bytes'] or path.stat().st_uid!=0 or path.stat().st_mode&0o022:bad.append(entry['path'])
if bad:raise RuntimeError('Release hash/ownership/mode failure')
state=pathlib.Path('/var/lib/racing-bois-staging');privacy={}
for path in [state,state/'realm',state/'realm/realm.sqlite3',state/'backup-key',root/'backups']:
    mode=stat.S_IMODE(path.stat().st_mode)
    if mode&0o077:raise RuntimeError('Private path is accessible to another Unix identity')
    privacy[str(path)]=oct(mode)
services={}
for name in ['racing-bois-staging','racing-bois-backup.timer','racing-bois-monitor.timer','caddy']:
    active=subprocess.check_output(['systemctl','is-active',name],text=True).strip()
    if active!='active':raise RuntimeError('Required service not active')
    services[name]=active
properties=subprocess.check_output(['systemctl','show','racing-bois-staging','-p','CPUQuotaPerSecUSec','-p','MemoryHigh','-p','MemoryMax','-p','TasksMax','-p','NRestarts','-p','MainPID'],text=True)
resource_limits=dict(line.split('=',1) for line in properties.splitlines())
running_executable=pathlib.Path('/proc')/resource_limits['MainPID']/'exe'
if running_executable.resolve()!=current/'server/RacingBois.Server.Host':raise RuntimeError('Running process does not match active release')
with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=5) as response:health=json.load(response)
listeners=subprocess.check_output(['ss','-lnt'],text=True)
loopback='127.0.0.1:18080' in listeners and '0.0.0.0:18080' not in listeners and '[::]:18080' not in listeners
if not loopback:raise RuntimeError('Backend listener escaped loopback')
metadata_request=urllib.request.Request('http://169.254.169.254/opc/v2/instance/',headers={'Authorization':'Bearer Oracle'})
with urllib.request.urlopen(metadata_request,timeout=3) as response:instance=json.load(response)
memory={line.split(':')[0]:int(line.split()[1])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
report={'schemaVersion':1,'status':'passed','generatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'releaseId':manifest['releaseId'],
 'vm':{'hostname':platform.node(),'architecture':platform.machine(),'logicalCpus':os.cpu_count(),'region':instance.get('region'),'shape':instance.get('shape'),'memoryBytes':memory},
 'sourceSha256':manifest['source']['sha256'],'testSourceSha256':manifest['testSource']['sha256'],'verifiedFiles':len(manifest['files']),
 'privateModes':privacy,'services':services,'loopbackOnly':loopback,'runningExecutableMatchesRelease':True,'resourceLimits':resource_limits,'health':health}
print(json.dumps(report))
