"""Independent double-precision triangle-intersection audit of authored lightmap UVs."""
from pathlib import Path
import hashlib,json
import numpy as np
import shapely
from shapely import STRtree,Polygon
ROOT=Path(__file__).resolve().parents[3];DOC=ROOT/'docs/p08/golden/garage/v3'
source=DOC/'uv-author-mcp.json';raw=source.read_bytes();result=json.loads(raw)['result']['structuredContent']['result']
data=json.loads(result.split('GARAGE_LIGHTMAP_UV ',1)[1]);rows=[]
for mesh in data['meshes']:
    faces=mesh['uvTriangles'];polygons=np.array([Polygon(v) for v in faces],dtype=object);tree=STRtree(polygons)
    pairs=tree.query(polygons,predicate='intersects');pairs=pairs[:,pairs[0]<pairs[1]]
    intersections=shapely.intersection(polygons[pairs[0]],polygons[pairs[1]])
    areas=shapely.area(intersections);bad=areas>1e-14
    row={k:v for k,v in mesh.items() if k!='uvTriangles'}
    row.update(overlappingTrianglePairs=int(np.count_nonzero(bad)),maximumOverlapArea=float(areas.max()) if len(areas) else 0)
    rows.append(row)
    print(row['name'],row['degenerateUvTriangles'],row['overlappingTrianglePairs'],flush=True)
report={'schema':1,'passed':all(r['degenerateUvTriangles']==r['overlappingTrianglePairs']==0 and r['geometryUv0NormalsUnchanged'] for r in rows),
        'sourceReceiptSha256':hashlib.sha256(raw).hexdigest(),'method':'Shapely2.0.7 STRtree and exact triangle polygon intersections; shared edges have zero area.',
        'triangleOverlapAreaTolerance':1e-14,'meshCount':len(rows),'triangles':sum(r['triangles'] for r in rows),'meshes':rows,'visualAccepted':False}
(DOC/'uv-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
assert report['passed'],'Authored UV audit failed'
print('GARAGE_UV_PASS',report['meshCount'],report['triangles'])
