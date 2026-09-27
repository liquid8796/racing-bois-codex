"""Bounded anonymous downloads for the explicitly approved local TripoSR trial."""
from pathlib import Path
import concurrent.futures
import hashlib
import html
import json
import re
import threading
import urllib.parse
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[3]
TRIAL=ROOT/'_local/p08-local3d'
LIMIT=6_000_000_000
CODE='107cefdc244c39106fa830359024f6a2f1c78871'
MODEL='5b521936b01fbe1890f6f9baed0254ab6351c04a'
lock=threading.Lock()
ledger={'networkBytes':30_000_000,'runtimeReservationBytes':30_000_000,'limitBytes':LIMIT,'files':[]}
ledger_path=TRIAL/'evidence/downloads.json'
if ledger_path.exists():ledger=json.loads(ledger_path.read_text())

def request(url,method='GET'):
    return urllib.request.Request(url,method=method,headers={'User-Agent':'RacingBois-bounded-local-TripoSR/1.0'})
def save_ledger():
    ledger_path.parent.mkdir(parents=True,exist_ok=True)
    ledger_path.write_text(json.dumps(ledger,indent=2)+'\n')
def wheel(name,version):
    index=urllib.request.urlopen(request('https://download.pytorch.org/whl/cu126/'+name+'/'),timeout=30).read().decode()
    wanted=f'{name}-{version}+cu126-cp310-cp310-win_amd64.whl'
    for link in re.findall(r'href="([^"]+)"',index):
        decoded=urllib.parse.unquote(html.unescape(link))
        if wanted in decoded:
            url,fragment=html.unescape(link).split('#',1)
            if url.startswith('//'):url='https:'+url
            url=urllib.parse.urljoin('https://download.pytorch.org',url)
            size=int(urllib.request.urlopen(request(url,'HEAD'),timeout=30).headers['Content-Length'])
            return {'url':url,'path':'downloads/'+wanted,'sha256':fragment.split('sha256=',1)[1],'size':size}
    raise RuntimeError('Exact official wheel not found: '+wanted)

tree=json.load(urllib.request.urlopen(request('https://huggingface.co/api/models/stabilityai/TripoSR/tree/'+MODEL+'?recursive=true'),timeout=30))
checkpoint=next(item for item in tree if item['path']=='model.ckpt')
jobs=[
    wheel('torch','2.7.1'),wheel('torchvision','0.22.1'),
    {'url':'https://huggingface.co/stabilityai/TripoSR/resolve/'+MODEL+'/model.ckpt','path':'models/TripoSR/model.ckpt','sha256':checkpoint['lfs']['oid'],'size':checkpoint['size']},
    {'url':'https://huggingface.co/stabilityai/TripoSR/resolve/'+MODEL+'/config.yaml','path':'models/TripoSR/config.yaml','size':987},
    {'url':'https://codeload.github.com/VAST-AI-Research/TripoSR/zip/'+CODE,'path':'downloads/TripoSR-'+CODE+'.zip','maxSize':100_000_000}
]
assert sum(job.get('size',job.get('maxSize',0)) for job in jobs)+ledger['networkBytes']<LIMIT

def fetch(job):
    destination=TRIAL/job['path'];destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        digest=hashlib.sha256(destination.read_bytes()).hexdigest()
        if job.get('sha256') and digest!=job['sha256']:raise RuntimeError('Existing file hash mismatch: '+job['path'])
        print('REUSE',job['path'],flush=True)
        return
    partial=destination.with_name(destination.name+'.part')
    if partial.exists():raise RuntimeError('Partial download requires explicit budget-aware resume: '+str(partial))
    digest=hashlib.sha256();received=0;announced=0
    with urllib.request.urlopen(request(job['url']),timeout=90) as response, partial.open('wb') as output:
        while True:
            data=response.read(2*1024*1024)
            if not data:break
            with lock:
                if ledger['networkBytes']+len(data)>LIMIT:raise RuntimeError('Approved download budget reached')
                ledger['networkBytes']+=len(data)
            output.write(data);digest.update(data);received+=len(data)
            if received>job.get('size',job.get('maxSize',LIMIT)):raise RuntimeError('Download exceeded declared size')
            if received-announced>=256*1024*1024:
                with lock:save_ledger()
                print('DOWNLOADING',job['path'],received,flush=True);announced=received
    if job.get('size') and received!=job['size']:raise RuntimeError('Download size mismatch')
    if job.get('sha256') and digest.hexdigest()!=job['sha256']:raise RuntimeError('Download hash mismatch')
    partial.replace(destination)
    with lock:
        ledger['files'].append({'path':job['path'],'url':job['url'],'bytes':received,'sha256':digest.hexdigest()});save_ledger()
    print('VERIFIED',job['path'],received,flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(fetch,jobs))
archive=TRIAL/'downloads'/('TripoSR-'+CODE+'.zip')
source_root=TRIAL/'source'
with zipfile.ZipFile(archive) as bundle:
    for item in bundle.infolist():
        path=source_root/item.filename
        if not path.resolve().is_relative_to(source_root.resolve()) or item.filename.startswith('/') or ((item.external_attr>>16)&0o170000)==0o120000:
            raise RuntimeError('Unsafe source archive member')
    bundle.extractall(source_root)
ledger['codeCommit']=CODE;ledger['modelCommit']=MODEL
with lock:save_ledger()
print('LOCAL3D_REQUIRED_DOWNLOADS_COMPLETE',ledger['networkBytes'],flush=True)
