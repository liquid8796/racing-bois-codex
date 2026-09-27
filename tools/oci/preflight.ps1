param(
    [string]$TargetHost = '158.180.59.36',
    [string]$SshUser = 'ubuntu',
    [string]$IdentityFile = 'C:\Users\Liquid\.ssh\jarvis_oci_ed25519'
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$outputPath = Join-Path $projectRoot 'docs/p02/oci/preflight.json'
$remoteScript = @'
import datetime,json,os,platform,shutil,subprocess
def output(command):
    p=subprocess.run(command,capture_output=True,text=True,timeout=10)
    return {'exit_code':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
memory={}
with open('/proc/meminfo') as f:
    for line in f:
        key,value=line.split(':',1)
        if key in ['MemTotal','MemAvailable','SwapTotal','SwapFree']:memory[key]=value.strip()
disk=shutil.disk_usage('/')
result={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'read_only':True,'hostname':platform.node(),'architecture':platform.machine(),
        'logical_cpus':os.cpu_count(),'memory':memory,
        'root_disk_bytes':{'total':disk.total,'used':disk.used,'free':disk.free},
        'listening_tcp':output(['ss','-lnt']),
        'runtime_paths':{name:shutil.which(name) for name in ['dotnet','docker','nginx','caddy','python3']}}
print(json.dumps(result,indent=2))
'@
$result = $remoteScript | & ssh -i $IdentityFile -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 "$SshUser@$TargetHost" 'python3 -'
if ($LASTEXITCODE -ne 0) { throw "SSH preflight failed with exit $LASTEXITCODE" }
$parsed = ($result -join "`n") | ConvertFrom-Json
New-Item -ItemType Directory -Path (Split-Path $outputPath) -Force | Out-Null
$parsed | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
$parsed | ConvertTo-Json -Depth 8
