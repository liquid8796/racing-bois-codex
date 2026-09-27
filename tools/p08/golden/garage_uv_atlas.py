"""Offline xatlas parameterization, never a geometry or texture rewrite."""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
import xatlas
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'_local/p08-garage-v3-staging'
parser=argparse.ArgumentParser();parser.add_argument('--first',action='store_true');args=parser.parse_args()
source=BASE/'uv-topology.json';meshes=json.loads(source.read_text(encoding='utf-8'));output=[]
for row in meshes[:1] if args.first else meshes:
    started=time.monotonic();vertices=np.asarray(row['vertices'],dtype=np.float32);faces=np.asarray(row['triangles'],dtype=np.uint32)
    atlas=xatlas.Atlas();atlas.add_mesh(vertices,faces)
    options=xatlas.PackOptions();options.resolution=1024;options.padding=4;options.bilinear=True
    atlas.generate(pack_options=options)
    mapping,indices,uv=atlas[0]
    assert np.array_equal(mapping[indices],faces),'Parameterizer changed face correspondence'
    corners=uv[indices];a=corners[:,1]-corners[:,0];b=corners[:,2]-corners[:,0]
    areas=np.abs(a[:,0].astype(float)*b[:,1]-a[:,1].astype(float)*b[:,0])
    assert np.isfinite(corners).all() and corners.min()>=0 and corners.max()<=1
    bad=int(np.count_nonzero(areas<=1e-14))
    # A shared polygon corner may not receive contradictory chart coordinates.
    loops=np.full((row['loopCount'],2),np.nan,dtype=np.float32);conflicts=0
    for tri,values in zip(row['loops'],corners):
        for index,value in zip(tri,values):
            if np.isfinite(loops[index]).all() and not np.array_equal(loops[index],value):conflicts+=1
            loops[index]=value
    result={'name':row['name'],'triangles':len(faces),'degenerateUvTriangles':bad,'loopConflicts':conflicts,
            'minimumUvCross':float(areas.min()),'atlasSize':[atlas.width,atlas.height],
            'seconds':time.monotonic()-started,'loops':loops.tolist()}
    output.append(result);print(json.dumps({k:v for k,v in result.items() if k!='loops'}),flush=True)
    assert bad==0 and conflicts==0 and np.isfinite(loops).all(),'Cannot assign valid second UV channel'
target=BASE/('uv-atlas-first.json' if args.first else 'uv-atlas.json')
target.write_text(json.dumps({'inputSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'xatlasVersion':'0.0.9','meshes':output}),encoding='utf-8')
