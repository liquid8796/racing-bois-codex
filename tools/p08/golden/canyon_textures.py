"""Pack inspected CC0 PBR inputs into Unity material conventions, locally."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'ArtSource/P08/Golden/Canyon/Materials'
OUT=ROOT/'Assets/RacingBois/Art/P08/Golden/Canyon/Textures'
OUT.mkdir(parents=True,exist_ok=True)
records=[]

def scalar8(path):
    """Normalize PNG scalar precision; Pillow I;16 -> L would saturate values."""
    source=Image.open(path)
    values=np.asarray(source)
    if source.mode in ('I;16','I;16B','I;16L','I'):
        return np.clip(np.rint(values.astype(np.float64)/257.0),0,255).astype(np.uint8)
    if source.mode=='F':
        return np.clip(np.rint(values.astype(np.float64)*255.0),0,255).astype(np.uint8)
    return np.asarray(source.convert('L'),dtype=np.uint8)

def write(name,base,rough,normal=None,metal=0,ao=None):
    base=np.asarray(base,dtype=np.uint8)
    h,w=base.shape[:2]
    Image.fromarray(base,'RGB').save(OUT/f'{name}_BaseColor.png')
    if normal is None:
        normal=np.zeros((h,w,3),dtype=np.uint8);normal[:]=[128,128,255]
    Image.fromarray(np.asarray(normal,dtype=np.uint8),'RGB').save(OUT/f'{name}_Normal.png')
    rgba=np.zeros((h,w,4),dtype=np.uint8);rgba[:,:,0]=metal;rgba[:,:,3]=255-np.asarray(rough,dtype=np.uint8)
    Image.fromarray(rgba,'RGBA').save(OUT/f'{name}_MetallicSmoothness.png')
    Image.fromarray(np.asarray(rough,dtype=np.uint8),'L').save(OUT/f'{name}_Roughness.png')
    if ao is not None:
        occ=np.empty((h,w,3),dtype=np.uint8);occ[:]=255;occ[:,:,1]=np.asarray(ao,dtype=np.uint8)
        Image.fromarray(occ,'RGB').save(OUT/f'{name}_Occlusion.png')
    records.append({'name':name,'size':[w,h],'metallic':metal/255,'normalConvention':'OpenGL tangent normal; Unity import and actual lighting inspection required'})

for logical,folder in [('Canyon_Sandstone','rock_face'),('Canyon_Asphalt','asphalt_02'),('Canyon_Gravel','brown_mud_rocks_01')]:
    d=SOURCE/folder
    base=np.array(Image.open(d/f'{folder}_Diffuse_2k.png').convert('RGB'))
    # Concept sandstone has ochre mineral coloration; preserve the scanned surface.
    tint=[1.45,1.25,1.08] if logical=='Canyon_Sandstone' else [1.08,1.03,.94] if logical=='Canyon_Gravel' else [.65,.65,.63]
    base=np.clip(base.astype(float)*np.array(tint),0,255).astype(np.uint8)
    write(logical,base,scalar8(d/f'{folder}_Rough_2k.png'),
          np.array(Image.open(d/f'{folder}_nor_gl_2k.png').convert('RGB')),ao=scalar8(d/f'{folder}_AO_2k.png'))

rng=np.random.default_rng(84721)
for name,color,rough,metal in [('Canyon_Galvanized',[125,130,126],135,225),('Canyon_Reflector',[208,118,10],145,0),('Canyon_YellowPaint',[181,130,39],215,0),('Canyon_WhitePaint',[189,181,155],220,0),('Canyon_Sage',[125,129,94],230,0),('Canyon_DryGrass',[161,126,65],234,0),('Canyon_Wood',[94,83,61],238,0)]:
    n=512
    noise=rng.normal(0,7,(n,n))
    if name=='Canyon_Galvanized':
        coarse=np.array(Image.fromarray(rng.integers(0,45,(32,32),dtype=np.uint8),'L').resize((n,n),Image.Resampling.BILINEAR)).astype(float)-22
        noise+=coarse
    if name=='Canyon_Sage':noise+=np.linspace(-22,18,n)[:,None]
    base=np.clip(np.array(color)[None,None,:]+noise[:,:,None],0,255).astype(np.uint8)
    write(name,base,np.clip(rough+noise,0,255).astype(np.uint8),metal=metal)

for i,slug in enumerate(['namaqualand_cliff_01','namaqualand_cliff_02','namaqualand_boulder_02'],1):
    d=ROOT/'ArtSource/P08/Golden/Canyon/SourceModels'/slug
    base=np.array(Image.open(d/(slug+'_Diffuse.jpg')).convert('RGB'))
    base=np.clip(base.astype(float)*np.array([1.25,1.04,.83]),0,255).astype(np.uint8)
    write('Canyon_Cliff%02d'%i,base,scalar8(d/(slug+'_Rough.png')),np.array(Image.open(d/(slug+'_nor_gl.png')).convert('RGB')),ao=scalar8(d/(slug+'_AO.png')))

receipt={'recipe':'tools/p08/golden/canyon_textures.py','inputs':'ArtSource/P08/Golden/Canyon/Materials/PROVENANCE.json','materials':records,'files':[]}
for p in sorted(OUT.glob('*.png')):receipt['files'].append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'docs/p08/golden/canyon').mkdir(parents=True,exist_ok=True)
(ROOT/'docs/p08/golden/canyon/textures.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('CANYON_TEXTURES',len(records),'materials',len(receipt['files']),'maps')
