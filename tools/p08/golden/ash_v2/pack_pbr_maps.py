"""Numerically pack real Blender bake channels into Unity URP texture inputs."""
from pathlib import Path
from PIL import Image
import hashlib,json
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
RAW=ROOT/'ArtSource/P08/Golden/Ash/V2/BakeIntermediate'
OUT=ROOT/'Assets/RacingBois/Art/P08/Golden/Ash/V2/Textures'
EVIDENCE=ROOT/'docs/p08/golden/ash/v2'
receipt=json.loads((EVIDENCE/'prepare_bake-uv0-mcp.json').read_text())
text='\n'.join(x.get('text','') for x in receipt['result']['content'])
metadata=json.loads(text.split('ASH_BAKE_PREP ',1)[1])['materials']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=[]
for spec in metadata:
    name=spec['sourceName'];size=spec['size'];channels={}
    for channel in ['BaseColor','Normal','Metallic','Roughness','Alpha','Occlusion']:
        path=RAW/f'{name}_{channel}.png'
        image=Image.open(path).convert('RGBA')
        assert image.size==(size,size),(path,image.size)
        channels[channel]=np.asarray(image)
    covered=channels['Alpha'][:,:,0]>128
    assert covered.sum()>32,(name,'empty bake')
    normal=channels['Normal'][:,:,:3].astype(np.float64)/127.5-1
    lengths=np.sqrt(np.square(normal[covered]).sum(axis=1))
    assert np.quantile(lengths,.01)>.85 and np.quantile(lengths,.99)<1.15,(name,'invalid tangent normals')
    color=channels['BaseColor'].copy()
    color[:,:,3]=channels['Alpha'][:,:,0] if spec['alpha'] else 255
    mask=np.empty_like(color)
    mask[:,:,0]=channels['Metallic'][:,:,0]
    mask[:,:,1]=channels['Occlusion'][:,:,0]
    mask[:,:,2]=0
    mask[:,:,3]=255-channels['Roughness'][:,:,0]
    files={}
    for channel,pixels in [('BaseColor',color),('Normal',channels['Normal']),('MetallicSmoothness',mask),('Occlusion',channels['Occlusion'])]:
        path=OUT/f'{name}_{channel}.png';Image.fromarray(pixels).save(path)
        files[channel]={'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size}
    result.append({'sourceName':name,'runtimeMaterial':name+'_Baked','size':size,'transparent':spec['alpha'],'doubleSided':spec['alpha'],
                   'coverageFraction':float(covered.mean()),'normalLengthP01':float(np.quantile(lengths,.01)),
                   'normalLengthP99':float(np.quantile(lengths,.99)),
                   'rawInputs':{channel:sha(RAW/f'{name}_{channel}.png') for channel in channels},'files':files})
report={'scope':'Real Blender baked channels packed for URP; no visual fidelity or performance acceptance.',
        'materialCount':len(result),'materials':result,'outputBytes':sum(f['bytes'] for r in result for f in r['files'].values())}
(EVIDENCE/'pbr-maps.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'materials':len(result),'outputBytes':report['outputBytes'],'normalValidation':'passed'}))
