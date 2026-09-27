#!/usr/bin/env python3
"""An empty staging realm only: prove automatic rollback when a deliberately failing startup is promoted."""
import datetime,hashlib,json,os,pathlib,sqlite3,subprocess,time,urllib.request,uuid
from contextlib import closing
root=pathlib.Path('/srv/racing-bois');current=(root/'current').resolve();original=json.loads((current/'release.json').read_text())
with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=5) as response:health=json.load(response)
if health['multiplayer']['roomCount'] or health['multiplayer']['sessionCount']:raise RuntimeError('Refusing rollback drill while a room/session exists')
def durable_summary():
    with closing(sqlite3.connect('file:/var/lib/racing-bois-staging/realm/realm.sqlite3?mode=ro',uri=True)) as database:
        return {'realm':database.execute('SELECT realm_id,kind FROM realm').fetchone(),'profiles':database.execute('SELECT count(*),coalesce(sum(credits),0) FROM profiles').fetchone(),
                'ledger':database.execute('SELECT count(*),coalesce(sum(delta),0) FROM ledger').fetchone(),'receipts':database.execute('SELECT count(*) FROM receipts').fetchone()}
before=durable_summary();identifier='p09-failed-start-'+uuid.uuid4().hex[:8];fixture=root/'releases'/identifier
(fixture/'server').mkdir(parents=True,mode=0o755);binary=fixture/'server/RacingBois.Server.Host';binary.write_text('#!/bin/sh\nexit 77\n');binary.chmod(0o755)
(fixture/'release.json').write_text(json.dumps({'releaseId':identifier,'scope':'Intentional failing-startup rollback fixture; never a valid game release','files':[{'path':'server/RacingBois.Server.Host','bytes':binary.stat().st_size,'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}]}))
environment=os.environ.copy();environment['RB_READY_ATTEMPTS']='5';began=time.monotonic()
result=subprocess.run(['/bin/bash',str(root/'ops/activate.sh'),identifier],env=environment,capture_output=True,text=True,timeout=45)
elapsed=time.monotonic()-began
if result.returncode!=1 or '"status":"rolled_back"' not in result.stdout or (root/'current').resolve()!=current:raise RuntimeError('Automatic rollback failed')
with urllib.request.urlopen('http://127.0.0.1:18080/ready',timeout=5) as response:ready=json.load(response)
if ready['status']!='ready' or durable_summary()!=before:raise RuntimeError('Rollback did not restore readiness and durable balances/receipts')
print(json.dumps({'status':'passed','generatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'activeReleaseBefore':original['releaseId'],'activeReleaseAfter':original['releaseId'],
                 'failedStartupFixture':identifier,'rollbackElapsedSeconds':elapsed,'activationExitCode':result.returncode,'readinessRestored':True,'durableIdentityBalancesLedgerReceiptsPreserved':True,
                 'scope':'Deliberately failing empty-staging startup fixture; only Racing Bois service affected; no live player rooms existed.'}))
