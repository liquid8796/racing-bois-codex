from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'ArtSource/P08/Golden/Garage/Materials';OUT.mkdir(parents=True,exist_ok=True)
jobs=[]
for slug in ['hangar_concrete_floor','concrete_wall_007']:
    directory=OUT/slug;directory.mkdir(exist_ok=True)
    request=urllib.request.Request('https://api.polyhaven.com/files/'+slug,headers={'User-Agent':'RacingBois-local-garage-authoring/1.0'})
    metadata=json.load(urllib.request.urlopen(request,timeout=30));(directory/'files-source.json').write_text(json.dumps(metadata,indent=2))
    for role in ['Diffuse','nor_gl','Rough','AO']:jobs.append((slug,role,metadata[role]['2k']['png']))
def fetch(job):
    slug,role,entry=job;path=OUT/slug/(slug+'_'+role+'_2k.png')
    if path.exists():data=path.read_bytes()
    else:
        request=urllib.request.Request(entry['url'],headers={'User-Agent':'RacingBois-local-garage-authoring/1.0'})
        data=urllib.request.urlopen(request,timeout=90).read();path.write_bytes(data)
    assert hashlib.md5(data).hexdigest()==entry['md5']
    return {'asset':slug,'role':role,'path':path.relative_to(ROOT).as_posix(),'url':entry['url'],'md5':entry['md5'],'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:files=list(pool.map(fetch,jobs))
(OUT/'PROVENANCE.json').write_text(json.dumps({'license':'CC0','licenseUrl':'https://polyhaven.com/license','pages':['https://polyhaven.com/a/hangar_concrete_floor','https://polyhaven.com/a/concrete_wall_007'],'purpose':'Surface inputs for the original Racing Bois garage environment; geometry follows the locked generated concept.','files':files},indent=2)+'\n')
print('GARAGE_CC0_MAPS_VERIFIED',len(files),'bytes',sum(item['bytes'] for item in files))
