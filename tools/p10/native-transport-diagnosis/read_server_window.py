"""Read a bounded journal window and emit only allowlisted aggregate failure classes."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[3]
remote_script=r'''
import collections,datetime,json,re,subprocess,urllib.request
begin='2026-09-26 23:39:55 UTC';end='2026-09-26 23:41:50 UTC'
result=subprocess.run(['journalctl','-u','racing-bois-staging','--since',begin,'--until',end,'--no-pager','-o','json'],capture_output=True,text=True,check=True)
classes=collections.Counter();events=[];total=0
for line in result.stdout.splitlines():
    item=json.loads(line);message=item.get('MESSAGE','');total+=1
    match=re.search(r'Multiplayer peer closed: (WebSocketException|OperationCanceledException|JsonException|InvalidDataException)',message)
    category='peer_closed_'+match.group(1) if match else None
    if category is None:
        match=re.search(r'Multiplayer command failed: (ArgumentException|InvalidOperationException|IOException)',message)
        if match:category='command_failed_'+match.group(1)
    if category:
        classes[category]+=1
        if len(events)<128:events.append({'utc':datetime.datetime.fromtimestamp(int(item['__REALTIME_TIMESTAMP'])/1000000,datetime.timezone.utc).isoformat(),'class':category})
with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=8) as response:health=json.load(response)
print(json.dumps({'scope':'Read-only exact native-run UTC window. Only allowlisted exception classes/times; no raw journal messages, identities, packets or credentials. Mailbox close reasons are not logged by current host.','windowUtc':[begin,end],'journalRows':total,'classes':dict(classes),'events':events,'multiplayerHealth':health.get('multiplayer',{})}))
'''
command=['ssh','-i','C:/Users/Liquid/.ssh/jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36','sudo -n python3 -']
result=subprocess.run(command,input=remote_script,capture_output=True,text=True,timeout=90)
if result.returncode:raise SystemExit('Read-only journal aggregation failed; raw output suppressed.')
report=json.loads(result.stdout);output=ROOT/'docs/p10/native-transport-diagnosis/server-window-0640.json';output.parent.mkdir(parents=True,exist_ok=True)
if output.exists():raise SystemExit('Immutable diagnostic receipt exists.')
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'journalRows':report['journalRows'],'classes':report['classes'],'receipt':str(output)}))
