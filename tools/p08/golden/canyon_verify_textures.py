"""Check current authored scalar maps against licensed source pixels and mask channels."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Assets/RacingBois/Art/P08/Golden/Canyon/Textures'
sources={
    'Canyon_Asphalt':('Materials/asphalt_02','asphalt_02_Rough_2k.png','asphalt_02_AO_2k.png'),
    'Canyon_Gravel':('Materials/brown_mud_rocks_01','brown_mud_rocks_01_Rough_2k.png','brown_mud_rocks_01_AO_2k.png'),
    'Canyon_Sandstone':('Materials/rock_face','rock_face_Rough_2k.png','rock_face_AO_2k.png'),
    'Canyon_Cliff01':('SourceModels/namaqualand_cliff_01','namaqualand_cliff_01_Rough.png','namaqualand_cliff_01_AO.png'),
    'Canyon_Cliff02':('SourceModels/namaqualand_cliff_02','namaqualand_cliff_02_Rough.png','namaqualand_cliff_02_AO.png'),
    'Canyon_Cliff03':('SourceModels/namaqualand_boulder_02','namaqualand_boulder_02_Rough.png','namaqualand_boulder_02_AO.png'),
}
checks=[];files=[]
for base in sorted(OUT.glob('*_BaseColor.png')):
    name=base.name.removesuffix('_BaseColor.png')
    rough=np.asarray(Image.open(OUT/(name+'_Roughness.png')))
    mask=np.asarray(Image.open(OUT/(name+'_MetallicSmoothness.png')))
    normal=np.asarray(Image.open(OUT/(name+'_Normal.png')))
    assert rough.dtype==np.uint8 and rough.ndim==2,name
    assert mask.shape==(*rough.shape,4) and normal.shape==(*rough.shape,3),name
    assert np.array_equal(mask[:,:,3],255-rough),name+' smoothness channel'
    assert (mask[:,:,0]==(225 if name=='Canyon_Galvanized' else 0)).all(),name+' metallic channel'
    assert np.ptp(rough)>0,name+' roughness variation lost'
    row={'material':name,'roughness8Min':int(rough.min()),'roughness8Max':int(rough.max()),'maskAlphaExactInverse':True,'dimensions':list(rough.shape)}
    if name in sources:
        directory,rough_file,ao_file=sources[name]
        for channel,file in [('rough',rough_file),('ao',ao_file)]:
            source=ROOT/'ArtSource/P08/Golden/Canyon'/directory/file
            original=Image.open(source)
            raw=np.asarray(original).astype(np.float64)
            divisor=257.0 if original.mode.startswith('I') else 1.0
            expected=np.rint(raw/divisor).astype(np.uint8)
            actual=rough if channel=='rough' else np.asarray(Image.open(OUT/(name+'_Occlusion.png')))[:,:,1]
            assert np.array_equal(actual,expected),name+' source scalar precision '+channel
            files.append(source)
            row[channel+'SourceMode']=original.mode
        row['sourceScalarPixelsPreserved']=True
    checks.append(row)
    files.extend(OUT.glob(name+'_*.png'))
files.extend([Path(__file__),ROOT/'tools/p08/golden/canyon_textures.py'])
receipt={'schema':1,'passed':True,'scope':'Source scalar normalization and Unity mask channel packing only; not visual acceptance.','checks':checks,'inputs':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(files))]}
(ROOT/'docs/p08/golden/canyon/scalar-packing-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('CANYON_SCALAR_MAPS_PASS',len(checks),'materials; exact source pixels, precision, channel layout and input hashes')
