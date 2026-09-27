"""Trusted public HTTPS + private SSH restart/backup/restore drill. QA secrets stay only in memory."""
import argparse, datetime, hashlib, json, pathlib, secrets, socket, ssl, subprocess, time, urllib.error, urllib.request, uuid

ROOT=pathlib.Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',default='docs/p09/live-ops.json')
parser.add_argument('--expected-release')
arguments=parser.parse_args()
HOST='racing-bois.158.180.59.36.sslip.io'; BASE='https://'+HOST
SSH=['ssh','-i',r'C:\Users\Liquid\.ssh\jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36']
checks=[]; requests=0
def check(value,name):
    if not value: raise RuntimeError(name)
    checks.append({'name':name,'passed':True})
def remote(command,stdin=None):
    result=subprocess.run(SSH+[command],input=stdin,text=True,capture_output=True,timeout=90)
    if result.returncode: raise RuntimeError('Remote operation failed: '+command.split()[0])
    return result.stdout.strip()
def request(path,body=None,token=None,origin=None):
    global requests
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    if origin: headers['Origin']=origin
    req=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
    requests+=1
    try:
        with urllib.request.urlopen(req,timeout=20) as response: return response.status,json.load(response)
    except urllib.error.HTTPError as error:
        payload=error.read()
        try: result=json.loads(payload)
        except json.JSONDecodeError: result={}
        return error.code,result

started=datetime.datetime.now(datetime.timezone.utc).isoformat()
deployed=json.loads(remote('cat /srv/racing-bois/current/release.json'))
if arguments.expected_release and deployed['releaseId']!=arguments.expected_release:raise RuntimeError('Unexpected deployed release')
with socket.create_connection((HOST,443),timeout=15) as raw:
    with ssl.create_default_context().wrap_socket(raw,server_hostname=HOST) as stream:
        certificate=stream.getpeercert(); tls={'validatedByOperatingSystem':True,'version':stream.version(),'peerCertificateSha256':hashlib.sha256(stream.getpeercert(True)).hexdigest(),
          'subject':certificate['subject'],'issuer':certificate['issuer'],'notBefore':certificate['notBefore'],'notAfter':certificate['notAfter'],'subjectAltName':certificate['subjectAltName']}
code,ready=request('/ready');check(code==200 and ready['status']=='ready','trusted_public_https_ready')
for path in ['/health','/health/','/multiplayer/health','/multiplayer/health/','/HEALTH','/metrics','/ws','/realm.sqlite3','/content/../realm.sqlite3']:
    status,_=request(path);check(status==404,'private_path_blocked:'+path)
username='qa_p09_'+uuid.uuid4().hex[:12]; password=secrets.token_urlsafe(36)
status,registered=request('/api/career',{'operation':'register','username':username,'password':password},origin=BASE)
check(status==200 and registered['ok'] and registered['profile']['realmKind']=='online' and registered['profile']['credits']==1000,'register_online_account_over_trusted_https')
token=registered['profileToken'];profile_id=registered['profile']['profileId']; transaction=str(uuid.uuid4())
command={'operation':'trade','bikeId':'rb-ember','transactionId':transaction}
_,trade=request('/api/career',command,token,BASE);check(trade['ok'] and trade['profile']['credits']==248,'server_authoritative_trade_balance')
_,repeat=request('/api/career',command,token,BASE);check(repeat['ok'] and repeat['profile']['credits']==248 and len(repeat['ledger'])==2,'idempotent_transaction_over_internet')
_,conflict=request('/api/career',{'operation':'buy','bikeId':'rb-kestrel','transactionId':transaction},token,BASE);check(conflict['code']=='transaction_conflict','transaction_intent_conflict_rejected')
_,export=request('/api/career',{'operation':'export'},token,BASE);check(export['code']=='offline_only','online_realm_rejects_offline_export')
status,_=request('/api/career',{'operation':'view'},token,'https://invalid.example');check(status==403,'cross_origin_request_rejected')
status,_=request('/api/career',{'operation':'view','credits':'999999'},token,BASE);check(status==400,'client_wallet_field_rejected')
restart_start=time.monotonic();remote('sudo -n systemctl restart racing-bois-staging')
for _ in range(20):
    try:
        status,value=request('/ready')
        if status==200:break
    except (OSError,ValueError):pass
    time.sleep(1)
else:raise RuntimeError('Service failed to become ready')
restart_seconds=time.monotonic()-restart_start
_,login=request('/api/career',{'operation':'login','username':username,'password':password},origin=BASE)
check(login['ok'] and login['profile']['profileId']==profile_id and login['profile']['credits']==248,'restart_preserves_account_identity_balance')
token=login['profileToken'];_,replay=request('/api/career',command,token,BASE)
check(replay['ok'] and replay['profile']['credits']==248 and len(replay['ledger'])==2,'restart_preserves_idempotent_receipt')
remote('sudo -n systemctl start racing-bois-backup')
backup=json.loads(remote('sudo -n cat /srv/racing-bois/backups/latest.json'))
restore=json.loads(remote('sudo -n -u racing-bois-staging python3 /srv/racing-bois/ops/restore-drill.py'))
check(backup['stateSha256']==restore['stateSha256'] and backup['realmId']==restore['realmId'],'online_backup_and_isolated_restore_exact_state')
directory=restore['restoredDirectory']; expected='/var/lib/racing-bois-staging/restore-drills/'
if not directory.startswith(expected) or len(directory.removeprefix(expected))!=32:raise RuntimeError('Invalid restore directory')
unit='racing-bois-restore-'+uuid.uuid4().hex[:10]
remote('sudo -n systemd-run --unit='+unit+' --uid=racing-bois-staging --property=CPUQuota=50% --property=MemoryMax=512M --property=RuntimeMaxSec=180 /srv/racing-bois/current/server/RacingBois.Server.Host --Port 18180 --TrustLocalProxy true --RealmKind online --DataRoot '+directory+' --WebRoot /srv/racing-bois/assets')
try:
    remote("for attempt in $(seq 1 15); do curl --fail --silent http://127.0.0.1:18180/ready >/dev/null && exit 0; sleep 1; done; exit 1")
    validated=json.loads(remote('sudo -n -u racing-bois-staging python3 /srv/racing-bois/ops/validate-restored.py',json.dumps({'username':username,'password':password,'profileId':profile_id,'credits':248})))
    check(validated['status']=='passed','restored_server_projection_validation_and_account_login')
finally:remote('sudo -n systemctl stop '+unit)
health=json.loads(remote('curl --fail --silent http://127.0.0.1:18080/health'))
receipt={'schemaVersion':1,'status':'passed','startedUtc':started,'finishedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'releaseId':deployed['releaseId'],'sourceSha256':deployed['source']['sha256'],
         'endpoint':BASE,'requests':requests,'tls':tls,'ready':ready,'restartSeconds':restart_seconds,'backup':backup,'restore':restore,
         'healthAfter':health,'checks':checks,'scope':'One Windows Internet origin to Frankfurt staging; this is not multi-region or Unity desktop acceptance.'}
out=ROOT/arguments.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,indent=2))
print(json.dumps({'status':'passed','checks':len(checks),'report':str(out),'restartSeconds':restart_seconds,'tls':tls},indent=2))
