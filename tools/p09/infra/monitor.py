#!/usr/bin/env python3
"""Private bounded health sampling; no player IDs, credentials or raw logs are stored."""
import datetime,json,pathlib,shutil,ssl,socket,urllib.request
issues=[];now=datetime.datetime.now(datetime.timezone.utc)
root=pathlib.Path('/var/lib/racing-bois-staging')
try:
    with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=5) as response:health=json.load(response)
    multiplayer=health['multiplayer']
    if multiplayer['persistenceFailures']>0:issues.append('persistence_failure_counter_nonzero')
    if multiplayer['tickDurationHistogram']['p99UpperBoundMilliseconds'] is not None and multiplayer['tickDurationHistogram']['p99UpperBoundMilliseconds']>12:issues.append('tick_p99_above_budget')
except (OSError,ValueError,KeyError):health={};issues.append('health_unavailable')
free=shutil.disk_usage(root).free
if free<2*1024**3:issues.append('disk_free_below_2GiB')
try:
    backup=json.loads(pathlib.Path('/srv/racing-bois/backups/latest.json').read_text())
    backup_age=(now-datetime.datetime.fromisoformat(backup['createdUtc'])).total_seconds()
    if backup_age>7200:issues.append('backup_older_than_2h')
except (OSError,ValueError,KeyError):backup_age=None;issues.append('backup_receipt_unavailable')
try:
    host='racing-bois.158.180.59.36.sslip.io'
    with socket.create_connection((host,443),timeout=8) as connection:
        with ssl.create_default_context().wrap_socket(connection,server_hostname=host) as tls:
            expiry=ssl.cert_time_to_seconds(tls.getpeercert()['notAfter'])
    cert_days=(expiry-now.timestamp())/86400
    if cert_days<7:issues.append('certificate_expires_under_7d')
except (OSError,ValueError,KeyError):cert_days=None;issues.append('certificate_validation_failed')
report={'generatedUtc':now.isoformat(),'status':'passed' if not issues else 'attention','issues':issues,'diskFreeBytes':free,'backupAgeSeconds':backup_age,'certificateDaysRemaining':cert_days,'health':health}
path=root/'monitor.json';tmp=root/'monitor.pending';tmp.write_text(json.dumps(report,indent=2));tmp.replace(path)
print(json.dumps({'status':report['status'],'issues':issues}))
