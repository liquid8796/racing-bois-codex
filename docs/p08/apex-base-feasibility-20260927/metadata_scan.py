"""Public metadata only: no mesh, texture, source archive, account or viewer extraction."""
from pathlib import Path
import concurrent.futures,datetime as dt,gzip,hashlib,json,time,urllib.request
OUT=Path(__file__).parent
def get(url,limit=5_000_000):
    with urllib.request.urlopen(url,timeout=25) as response:
        raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError('Metadata size cap exceeded')
        return raw
url='https://huggingface.co/datasets/allenai/objaverse/resolve/main/lvis-annotations.json.gz'
raw=get(url,2_000_000);labels=json.loads(gzip.decompress(raw));uids=labels['motorcycle']
(OUT/'lvis-motorcycle.json').write_text(json.dumps({'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'category':'motorcycle','uids':uids},indent=2)+'\n')
def read(uid):
    url='https://api.sketchfab.com/v3/models/'+uid
    try:
        data=json.loads(get(url,1_000_000));user=data.get('user',{})
        return {'uid':uid,'api':url,'name':data.get('name'),'viewerUrl':data.get('viewerUrl'),'description':data.get('description'),'license':data.get('license'),
                'isDownloadable':data.get('isDownloadable'),'faceCount':data.get('faceCount'),'vertexCount':data.get('vertexCount'),'animationCount':data.get('animationCount'),
                'createdAt':data.get('createdAt'),'publishedAt':data.get('publishedAt'),'creator':{k:user.get(k) for k in ['uid','username','displayName','profileUrl']},
                'tags':[t.get('name') for t in data.get('tags',[])],'thumbnails':data.get('thumbnails'),'metadataSha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()}
    except Exception as e:return {'uid':uid,'api':url,'error':type(e).__name__+': '+str(e)[:120]}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for item in pool.map(read,uids):results.append(item)
report={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'Only LVIS category list and public per-object creator/license/preview metadata. No models downloaded. Current license is checked separately from the dataset license.','models':results}
(OUT/'sketchfab-lvis-motorcycles.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
for item in results:
    license=(item.get('license') or {}).get('slug')
    if license in ['by','cc0']:
        print(json.dumps({'uid':item['uid'],'name':item.get('name'),'license':license,'author':item.get('creator',{}).get('displayName'),'downloadable':item.get('isDownloadable'),'faces':item.get('faceCount'),'description':(item.get('description') or '')[:280]}),flush=True)
print('METADATA_OBJECTS',len(results),'ERRORS',sum('error' in i for i in results),flush=True)
