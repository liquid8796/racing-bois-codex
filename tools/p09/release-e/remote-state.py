"""Read-only safe shared-host and logical realm state; never emit keys or command lines."""
import datetime,hashlib,json,pathlib,platform,re,subprocess,sys,urllib.request
sys.path.insert(0,'/srv/racing-bois/ops')
from backup import inspect_database
def run(arguments):return subprocess.check_output(arguments,text=True).strip()
def digest(data):return hashlib.sha256(data).hexdigest()
configs={}
for name in ['/etc/caddy/Caddyfile','/etc/caddy/upstream.conf','/etc/caddy/conf.d/racing-bois.caddy']:
    path=pathlib.Path(name)
    configs[name]=digest(path.read_bytes()) if path.is_file() else None
firewall={};normalized_firewall={}
for executable in ['iptables-save','ip6tables-save']:
    result=subprocess.run([executable],capture_output=True,text=True)
    if result.returncode:raise RuntimeError('Cannot establish read-only firewall baseline')
    text='\n'.join(line for line in result.stdout.splitlines() if not line.startswith('#'))
    firewall[executable]=digest(text.encode())
    normalized_firewall[executable]=digest(re.sub(r'\[\d+:\d+\]','[COUNTERS]',text).encode())
with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=8) as response:health=json.load(response)
with urllib.request.urlopen('https://158.180.59.36.sslip.io/',timeout=20) as response:existing=response.status
units=json.loads(run(['systemctl','list-units','--type=service','--state=running','--output=json','--no-pager']))
current=pathlib.Path('/srv/racing-bois/current').resolve();manifest=json.loads((current/'release.json').read_text())
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hostname':platform.node(),'architecture':platform.machine(),
 'releaseId':manifest['releaseId'],'sourceSha256':manifest['source']['sha256'],'currentTarget':str(current),
 'realm':inspect_database(pathlib.Path('/var/lib/racing-bois-staging/realm/realm.sqlite3')),
 'caddyConfigSha256':configs,'firewallRulesSha256':firewall,'firewallCounterNormalizedSha256':normalized_firewall,'runningServices':sorted(unit['unit'] for unit in units),
 'existingSiteHttpStatus':existing,'health':health}))
