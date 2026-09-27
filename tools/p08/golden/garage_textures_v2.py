"""Pack inspected CC0 garage surfaces and authored small material atlases."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'ArtSource/P08/Golden/Garage/Materials'
OUT=ROOT/'Assets/RacingBois/Art/P08/Golden/Garage/V2/Textures'
DOC=ROOT/'docs/p08/golden/garage/v2'
OUT.mkdir(parents=True,exist_ok=True);DOC.mkdir(parents=True,exist_ok=True)
records=[]

def scalar(path):
    im=Image.open(path);a=np.asarray(im)
    if im.mode in ('I;16','I;16B','I;16L','I'):return np.clip(np.rint(a.astype(float)/257),0,255).astype(np.uint8)
    return np.asarray(im.convert('L'))

def write(name,base,rough,metal=0,normal=None,ao=None,emission=None):
    base=np.asarray(base,dtype=np.uint8);h,w=base.shape[:2]
    Image.fromarray(base).save(OUT/(name+'_BaseColor.png'))
    if normal is None:normal=np.broadcast_to(np.array([128,128,255],dtype=np.uint8),(h,w,3)).copy()
    Image.fromarray(normal).save(OUT/(name+'_Normal.png'))
    rough=np.broadcast_to(np.asarray(rough,dtype=np.uint8),(h,w)).copy()
    Image.fromarray(rough).save(OUT/(name+'_Roughness.png'))
    mask=np.zeros((h,w,4),dtype=np.uint8);mask[:,:,0]=metal;mask[:,:,3]=255-rough
    Image.fromarray(mask).save(OUT/(name+'_MetallicSmoothness.png'))
    if ao is not None:
        occ=np.full((h,w,3),255,dtype=np.uint8);occ[:,:,1]=ao
        Image.fromarray(occ).save(OUT/(name+'_Occlusion.png'))
    if emission is not None:Image.fromarray(np.broadcast_to(np.array(emission,dtype=np.uint8),(h,w,3)).copy()).save(OUT/(name+'_Emission.png'))
    records.append({'name':name,'resolution':w,'roughnessMin':int(rough.min()),'roughnessMax':int(rough.max()),'metallic':metal/255})

for name,slug,tint in [('Garage_Floor','hangar_concrete_floor',[1.42,1.40,1.38]),('Garage_Concrete','concrete_wall_007',[.71,.73,.76])]:
    d=SOURCE/slug;base=np.asarray(Image.open(d/(slug+'_Diffuse_2k.png')).convert('RGB'))
    base=np.clip(base.astype(float)*np.array(tint),0,255).astype(np.uint8)
    rough=scalar(d/(slug+'_Rough_2k.png'))
    # A polished clear surface retains the scan's roughness variation, with an
    # explicit coating range; this transformation is disclosed in the receipt.
    if name=='Garage_Floor':rough=np.rint(34+rough.astype(float)*.13).astype(np.uint8)
    write(name,base,rough,normal=np.asarray(Image.open(d/(slug+'_nor_gl_2k.png')).convert('RGB')),ao=scalar(d/(slug+'_AO_2k.png')))
    if name=='Garage_Concrete':
        write('Garage_NearConcrete',np.rint(base.astype(float)*.55).astype(np.uint8),rough,normal=np.asarray(Image.open(d/(slug+'_nor_gl_2k.png')).convert('RGB')),ao=scalar(d/(slug+'_AO_2k.png')))

rng=np.random.default_rng(72038);n=512
for name,color,rough,metal in [('Garage_PowderSteel',[35,37,37],108,0),('Garage_ToolSteel',[144,148,149],62,255),('Garage_Rubber',[17,18,18],186,0),('Garage_Wood',[110,83,50],150,0),('Garage_Cardboard',[114,88,56],222,0),('Garage_Amber',[181,97,14],140,0),('Garage_Cable',[21,22,22],170,0),('Garage_Lamp',[245,229,192],78,0),('Garage_HelmetShell',[49,51,50],55,0),('Garage_Visor',[13,16,18],33,0)]:
    noise=rng.normal(0,1.5,(n,n))
    if name=='Garage_Wood':
        streak=np.asarray(Image.fromarray(rng.integers(0,50,(512,16),dtype=np.uint8)).resize((n,n),Image.Resampling.BILINEAR)).astype(float)-25
        noise+=streak*.75
    base=np.clip(np.array(color)[None,None,:]+noise[:,:,None],0,255).astype(np.uint8)
    write(name,base,np.clip(rough+noise*2,0,255).astype(np.uint8),metal,emission=[255,183,94] if name=='Garage_Lamp' else None)

files=[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(OUT.glob('*.png'))]
(DOC/'textures.json').write_text(json.dumps({'materials':records,'files':files,'sourceProvenance':'ArtSource/P08/Golden/Garage/Materials/PROVENANCE.json','floorCoating':'roughness8 = round(34 + sourceRoughness8 * 0.13); sRGB diffuse multiplier [1.42,1.40,1.38]','wallTint':[.71,.73,.76],'normalConvention':'OpenGL','scalar16BitConversion':'round(value / 257), never saturating Pillow I;16 to L'},indent=2)+'\n')
print('GARAGE_TEXTURES',len(records),len(files))

