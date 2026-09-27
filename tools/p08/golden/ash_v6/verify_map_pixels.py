"""Read-only checks of real bake/packing outputs; no image editing."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[4];folder=ROOT/'ArtSource/P08/Golden/Ash/V6/Textures';raw=folder.parent/'BakeIntermediate';rows=[]
for role in ['Skin','EquipmentL0','EquipmentL1','EquipmentL2']:
    prefix='AshV6_'+role
    image={c:np.asarray(Image.open(folder/(prefix+'_'+c+'.png')).convert('RGBA')) for c in ['BaseColor','Normal','MetallicSmoothness','Occlusion']}
    rough=np.asarray(Image.open(raw/(prefix+'_Roughness.png')).convert('RGBA'))
    mask=image['MetallicSmoothness'];covered=image['BaseColor'][:,:,3]>128;norm=image['Normal'][:,:,:3].astype(float)/127.5-1
    lengths=np.linalg.norm(norm[covered],axis=1)
    assert covered.sum()>64
    assert mask[:,:,2].max()==0
    if role=='Skin':assert mask[:,:,0].max()==0
    else:
        metallic=np.asarray(Image.open(raw/(prefix+'_Metallic.png')).convert('RGBA'))
        assert int(np.abs(mask[:,:,0].astype(int)-metallic[:,:,0].astype(int)).max())<=1
    ao_error=int(np.abs(mask[:,:,1].astype(int)-image['Occlusion'][:,:,0].astype(int)).max())
    rough_error=int(np.abs(mask[:,:,3].astype(int)-(255-rough[:,:,0].astype(int))).max())
    assert ao_error<=1 and rough_error<=1,(role,ao_error,rough_error)
    p01,p99=np.quantile(lengths,[.01,.99]);assert p01>.85 and p99<1.15,(role,p01,p99)
    files={}
    for channel in image:
        p=folder/(prefix+'_'+channel+'.png')
        files[channel]={'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
        if channel!='MetallicSmoothness':assert p.read_bytes()==(raw/p.name).read_bytes()
    rows.append({'role':role,'size':list(image['BaseColor'].shape[:2]),'coverage':float(covered.mean()),'normalLengthP01':float(p01),'normalLengthP99':float(p99),
        'maximumAoChannelError8bit':ao_error,'maximumInvertedRoughnessError8bit':rough_error,'files':files})
report={'passed':True,'scope':'Read-only numeric checks of actual Blender PNG bakes and mask packing, not visual fidelity. Base/normal/AO copies are byte-identical to bake outputs.','materials':rows}
(ROOT/'docs/p08/golden/ash/v6/map-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'passed':True,'roles':len(rows),'newMaps':sum(len(r['files']) for r in rows),'maximumChannelError8bit':max(max(r['maximumAoChannelError8bit'],r['maximumInvertedRoughnessError8bit']) for r in rows)}))
