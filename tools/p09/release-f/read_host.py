"""Read-only OCI preflight; existing safe host inspector, no upload or activation."""
from pathlib import Path
import datetime as dt,json,subprocess
ROOT=Path(__file__).resolve().parents[3]
command=['ssh','-i','C:/Users/Liquid/.ssh/jarvis_oci_ed25519','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','ubuntu@158.180.59.36','sudo -n python3 -']
script=(ROOT/'tools/p09/release-e/remote-state.py').read_text()
run=subprocess.run(command,input=script,capture_output=True,text=True,timeout=90)
if run.returncode:raise SystemExit('Read-only preflight failed; raw output suppressed.')
state=json.loads(run.stdout);path=ROOT/'docs/p09/releases/f/preflight-host.json'
if path.exists():raise SystemExit('Immutable preflight receipt exists.')
path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
print(json.dumps({'scope':'Read-only OCI preflight; no activation/upload.','releaseId':state['releaseId'],'sourceSha256':state['sourceSha256'],
                  'architecture':state['architecture'],'unrelatedSiteStatus':state['existingSiteHttpStatus'],'receipt':str(path)}))
