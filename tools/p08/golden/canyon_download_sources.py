"""Download selected free CC0 geometry for local sculpting; verify upstream hashes."""
from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'ArtSource/P08/Golden/Canyon/SourceModels'
jobs=[]
for slug in ['namaqualand_cliff_01','namaqualand_cliff_02','namaqualand_boulder_02']:
    metadata=json.loads((OUT/(slug+'-files.json')).read_text())
    for kind,fmt in [('fbx','fbx'),('Diffuse','jpg'),('nor_gl','png'),('Rough','png'),('AO','png')]:
        info=metadata[kind]['2k'][fmt]
        jobs.append((slug,kind,fmt,info))
def fetch(job):
    slug,kind,fmt,info=job
    directory=OUT/slug;directory.mkdir(parents=True,exist_ok=True)
    path=directory/(slug+'_'+kind+'.'+fmt)
    if path.exists():data=path.read_bytes()
    else:
        request=urllib.request.Request(info['url'],headers={'User-Agent':'RacingBois-local-asset-review/1.0'})
        data=urllib.request.urlopen(request,timeout=90).read();path.write_bytes(data)
    assert hashlib.md5(data).hexdigest()==info['md5'],path
    return {'asset':slug,'kind':kind,'path':path.relative_to(ROOT).as_posix(),'url':info['url'],'md5':info['md5'],'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(fetch,jobs))
receipt={'license':'CC0','licenseUrl':'https://polyhaven.com/license','pages':['https://polyhaven.com/a/namaqualand_cliff_01','https://polyhaven.com/a/namaqualand_cliff_02','https://polyhaven.com/a/namaqualand_boulder_02'],'purpose':'Free photogrammetry inputs for a locally modified original Canyon composition; not original-game assets, not claimed as wholly self-authored scan geometry. Concept fidelity remains unaccepted.','files':records}
(OUT/'PROVENANCE.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('CC0_SOURCE_FILES',len(records),'bytes',sum(r['bytes'] for r in records),'verified MD5 and SHA256 recorded')
