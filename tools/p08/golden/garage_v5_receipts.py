"""Decode source audit receipts and cross-check packed/external texture bytes."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
DOC=ROOT/'docs/p08/golden/garage/v5'

def read_receipt(name,marker):
    value=json.loads((DOC/name).read_text(encoding='utf-8-sig'))
    text='\n'.join(item['text'] for item in value['result']['content'] if item['type']=='text')
    return json.JSONDecoder().raw_decode(text[text.index(marker)+len(marker):])[0]

materials=read_receipt('material-mcp.json','GARAGE_V5_MATERIAL ')
(DOC/'material-comparison-settings.json').write_text(json.dumps(materials,indent=2))
rows=[]
for image in materials['packedImages']:
    path=Path(image['filepath']);data=path.read_bytes();value=14695981039346656037
    for byte in data:value=((value^byte)*1099511628211)&18446744073709551615
    match=len(data)==image['bytes'] and f'{value:016x}'==image['packedFnv1a64']
    rows.append({'path':path.relative_to(ROOT).as_posix(),'externalSha256':hashlib.sha256(data).hexdigest(),
        'byteCount':len(data),'externalAndPackedFnv1a64':f'{value:016x}','matchesPackedFingerprintAndLength':match})
packed={'passed':all(r['matchesPackedFingerprintAndLength'] for r in rows),'images':len(rows),'files':rows,
    'scope':'Blender explicitly reloaded unchanged FILE PNGs, then packed. FNV1a64 plus length compare verifies packed byte fingerprint; external SHA256 binds source PNG. No SHA256 computed inside safe-mode Blender.'}
(DOC/'packed-texture-verification.json').write_text(json.dumps(packed,indent=2))
assert packed['passed']
triangles=read_receipt('uv-triangles-final-mcp.json','GARAGE_V5_TRIANGLES ')
(DOC/'uv-triangles-final.json').write_text(json.dumps(triangles,indent=2))
fix=read_receipt('uv-triangle-repair-mcp.json','GARAGE_V5_TRIANGLE_REPAIR ')
(DOC/'uv-triangle-repair.json').write_text(json.dumps(fix,indent=2))
print(json.dumps({'packedImagesPassed':len(rows),'additionalFaceProjections':fix['additionalFaces'],
    'trianglesByLod':{str(lod):sum(o['triangles'] for o in triangles['objects'] if f'_L{lod}_' in o['name']) for lod in range(3)},
    'primaryFailures':triangles['primaryFailures'],'physicalFailures':triangles['physicalFailures'],'lightmapFailures':triangles['lightmapFailures']}))
