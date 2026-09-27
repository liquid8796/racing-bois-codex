"""Anonymous, budgeted inputs for the approved isolated TripoSG trial.

No project image leaves the machine. This fetcher never executes downloaded
source and never accepts Hugging Face terms or sends cached credentials.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,urllib.request

ROOT=Path(__file__).resolve().parents[3];TRIAL=ROOT/'_local/p08-triposg'
CODE='fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c';MODEL='2c1c516d22d58db486a058d98d31bb6177344e06'
DOWNLOAD_CAP=10_000_000_000;DISK_CAP=20_000_000_000
LEDGER=TRIAL/'evidence/downloads.json';TRIAL.mkdir(parents=True,exist_ok=True);LEDGER.parent.mkdir(parents=True,exist_ok=True)
ledger=json.loads(LEDGER.read_text()) if LEDGER.exists() else {'newNetworkBytes':0,'downloadCapBytes':DOWNLOAD_CAP,'newDiskCapBytes':DISK_CAP,'files':[],'metadataRequests':[]}

def save():LEDGER.write_text(json.dumps(ledger,indent=2)+'\n')
def disk_bytes():return sum(p.stat().st_size for p in TRIAL.rglob('*') if p.is_file())
def request(url):return urllib.request.Request(url,headers={'User-Agent':'RacingBois-bounded-local-TripoSG/1.0'})
def meta(url):
    data=urllib.request.urlopen(request(url),timeout=45).read(4_000_001)
    if len(data)>4_000_000:raise RuntimeError('Unexpected metadata size')
    ledger['newNetworkBytes']+=len(data);ledger['metadataRequests'].append({'url':url,'bytes':len(data)});save()
    if ledger['newNetworkBytes']>DOWNLOAD_CAP:raise RuntimeError('Network budget exceeded')
    return json.loads(data)

def fetch(url,relative,size,sha256=None,git_blob=None):
    target=(TRIAL/relative).resolve();target.relative_to(TRIAL.resolve())
    if target.exists():
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        if sha256 and digest!=sha256:raise RuntimeError('Existing file hash mismatch: '+relative)
        if target.stat().st_size!=size:raise RuntimeError('Existing size mismatch: '+relative)
        return
    if ledger['newNetworkBytes']+size>DOWNLOAD_CAP or disk_bytes()+size>DISK_CAP:raise RuntimeError('Approved budget would be exceeded')
    target.parent.mkdir(parents=True,exist_ok=True);partial=target.with_suffix(target.suffix+'.part')
    if partial.exists():raise RuntimeError('Partial input needs an explicit budget-aware recovery: '+relative)
    received=0;digest=hashlib.sha256();last=0
    try:
        with urllib.request.urlopen(request(url),timeout=120) as response,partial.open('wb') as output:
            while True:
                block=response.read(2*1024*1024)
                if not block:break
                ledger['newNetworkBytes']+=len(block);received+=len(block)
                if ledger['newNetworkBytes']>DOWNLOAD_CAP or received>size:raise RuntimeError('Download exceeded declared budget/size')
                output.write(block);digest.update(block)
                if received-last>=128*1024*1024:save();print('FETCH',relative,received,flush=True);last=received
        if received!=size:raise RuntimeError('Truncated input: '+relative)
        if sha256 and digest.hexdigest()!=sha256:raise RuntimeError('SHA256 mismatch: '+relative)
        if git_blob:
            payload=partial.read_bytes();actual=hashlib.sha1(('blob '+str(len(payload))+'\0').encode()+payload).hexdigest()
            if actual!=git_blob:raise RuntimeError('Git blob mismatch: '+relative)
        partial.replace(target)
        ledger['files'].append({'path':relative,'url':url,'bytes':received,'sha256':digest.hexdigest(),'gitBlob':git_blob});save()
        print('VERIFIED',relative,received,flush=True)
    finally:save()

def source():
    tree=meta('https://api.github.com/repos/VAST-AI-Research/TripoSG/git/trees/'+CODE+'?recursive=1')
    assert not tree.get('truncated')
    selected=[x for x in tree['tree'] if x['type']=='blob' and ((x['path'].startswith('triposg/') and x['path'].endswith('.py')) or x['path'] in ['LICENSE','NOTICE','README.md','requirements.txt','scripts/image_process.py','scripts/inference_triposg.py'])]
    assert sum(x['size'] for x in selected)<2_000_000
    for row in selected:
        assert '..' not in Path(row['path']).parts
        fetch('https://raw.githubusercontent.com/VAST-AI-Research/TripoSG/'+CODE+'/'+row['path'],'source/'+row['path'],row['size'],git_blob=row['sha'])
    (TRIAL/'evidence/source-manifest.json').write_text(json.dumps({'commit':CODE,'files':selected,'sourceExecuted':False},indent=2)+'\n')

def weights(release_note):
    raise RuntimeError('Trial stopped by root: embedded HunyuanDiT/FlashVDM license restrictions remain unresolved. Do not download weights.')
    now=datetime.datetime.now(datetime.timezone.utc)
    assert now>=datetime.datetime(2026,9,27,1,1,tzinfo=datetime.timezone.utc),'OCI WAN baseline window not finished'
    assert release_note and len(release_note)>15,'Record the actual root WAN completion/release signal, not elapsed time alone'
    ledger['wanReleaseNote']=release_note;save()
    tree=meta('https://huggingface.co/api/models/VAST-AI/TripoSG/tree/'+MODEL+'?recursive=true')
    selected=[x for x in tree if x['type']=='file' and x['path'] not in ['.gitattributes','README.md']]
    for row in selected:fetch('https://huggingface.co/VAST-AI/TripoSG/resolve/'+MODEL+'/'+row['path'],'models/TripoSG/'+row['path'],row['size'],sha256=row.get('lfs',{}).get('oid'))
    (TRIAL/'evidence/model-manifest.json').write_text(json.dumps({'revision':MODEL,'files':selected},indent=2)+'\n')

parser=argparse.ArgumentParser();parser.add_argument('--source',action='store_true');parser.add_argument('--weights',action='store_true');parser.add_argument('--wan-release-note');args=parser.parse_args()
if args.source:source()
if args.weights:weights(args.wan_release_note)
ledger['observedDiskBytes']=disk_bytes();save();assert ledger['observedDiskBytes']<=DISK_CAP
print('TRIPOSG_BUDGET',ledger['newNetworkBytes'],ledger['observedDiskBytes'])
