"""Original physical-surface maps for the inspected Ash v2 construction sheet.

No image pixels are copied from the concept. Skin UV is a dedicated spherical
head layout; remaining surfaces intentionally reuse full-field material maps.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Assets/RacingBois/Art/P08/Golden/Ash'
OUT.mkdir(parents=True, exist_ok=True)
SPECS = {
    'Ash_Skin': (2048, (.48, .285, .175), .0, .54, 'skin'),
    'Ash_Jacket': (2048, (.066, .058, .045), .0, .56, 'leather'),
    'Ash_Amber': (1024, (.39, .195, .051), .0, .59, 'leather'),
    'Ash_Trousers': (1024, (.047, .050, .048), .0, .74, 'fabric'),
    'Ash_BootLeather': (1024, (.12, .057, .025), .0, .58, 'leather'),
    'Ash_Helmet': (1024, (.72, .69, .57), .0, .35, 'paint'),
    'Ash_Rubber': (512, (.019, .023, .024), .0, .76, 'rubber'),
    'Ash_Hair': (512, (.028, .020, .014), .0, .63, 'hair'),
    'Ash_Metal': (512, (.32, .275, .195), .82, .34, 'metal'),
    'Ash_Eye': (512, (.68, .67, .56), .0, .16, 'eye'),
    'Ash_Iris': (512, (.105, .071, .035), .0, .20, 'iris'),
    'Ash_Lip': (512, (.29, .115, .077), .0, .57, 'skin_detail'),
}

def low_noise(rng, size, cells):
    coarse = rng.integers(0, 256, (cells, cells), dtype=np.uint8)
    return np.asarray(Image.fromarray(coarse).resize((size,size),Image.Resampling.BICUBIC),dtype=np.float32)/255-.5

records=[]
for index,(name,(size,colour,metallic,roughness,kind)) in enumerate(SPECS.items()):
    rng=np.random.default_rng(68231+index)
    y,x=np.mgrid[0:size,0:size].astype(np.float32)
    u,v=x/size,y/size
    grain=rng.random((size,size),dtype=np.float32)-.5
    broad=low_noise(rng,size,16); medium=low_noise(rng,size,100)
    fine=low_noise(rng,size,300)
    if kind=='leather':
        grain_height=grain*.09+fine*.32+medium*.17
        variation=broad*.017+medium*.020+fine*.008
    elif kind=='fabric':
        weave=np.sin(u*np.pi*size)*np.sin(v*np.pi*size)
        grain_height=grain*.08+weave*.055+fine*.06
        variation=medium*.012+grain*.009
    elif kind=='hair':
        grain_height=np.sin(u*2*np.pi*130+medium*.7)*.10+grain*.03
        variation=grain*.006+medium*.008
    elif kind=='skin':
        grain_height=fine*.055+grain*.035
        variation=medium*.011+broad*.018+grain*.004
    elif kind=='metal':
        grain_height=np.sin(v*2*np.pi*size/3)*.06+grain*.04
        variation=medium*.025+grain*.02
    elif kind=='paint':
        grain_height=grain*.008
        variation=broad*.008+grain*.006
    else:
        grain_height=grain*.022
        variation=medium*.006+grain*.004
    rgb=np.clip(np.asarray(colour,dtype=np.float32)[None,None,:]+variation[:,:,None],.003,.97)
    if kind=='skin':
        # UV u=.5 is front centre; v grows from chin to scalp. Blend color is
        # skin shading only: facial anatomy is geometry, never pasted pixels.
        front=np.exp(-((u-.5)/.13)**6)
        cheeks=np.exp(-((np.abs(u-.5)-.065)/.025)**2-((v-.46)/.085)**2)
        beard=np.exp(-((u-.5)/.14)**6)*np.clip((.29-v)/.10,0,1)
        redness=cheeks*.032+front*np.exp(-((v-.52)/.13)**2)*.009
        rgb[:,:,0]+=redness;rgb[:,:,1]-=redness*.20
        rgb-=beard[:,:,None]*(.018+(grain[:,:,None]>.38)*.025)
    if kind=='iris':
        radius=np.sqrt((u-.5)**2+(v-.5)**2)
        ray=np.sin(np.arctan2(v-.5,u-.5)*63+radius*80)
        rgb+=ray[:,:,None]*.015
        rgb*=np.where(radius<.17,.13,1)[:,:,None]
    Image.fromarray(np.round(np.clip(rgb,0,1)*255).astype(np.uint8)).save(OUT/f'{name}_BaseColor.png')
    dx=np.roll(grain_height,-1,axis=1)-np.roll(grain_height,1,axis=1)
    dy=np.roll(grain_height,-1,axis=0)-np.roll(grain_height,1,axis=0)
    normal=np.dstack((-dx,-dy,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    Image.fromarray(np.round((normal*.5+.5)*255).astype(np.uint8)).save(OUT/f'{name}_Normal.png')
    rough=np.clip(roughness+broad*.07+grain*.04,.05,.95)
    mask=np.dstack((np.full_like(rough,metallic),np.ones_like(rough),np.zeros_like(rough),1-rough))
    Image.fromarray(np.round(mask*255).astype(np.uint8)).save(OUT/f'{name}_MetallicSmoothness.png')
    Image.fromarray(np.round(rough*255).astype(np.uint8)).save(OUT/f'{name}_Roughness.png')
    records.append({'material':name,'resolution':size,'surface':kind,'original':True})
(OUT/'surface-layout.json').write_text(json.dumps({'schema':1,'surfaces':records,'conceptPixelsCopied':False},indent=2)+'\n')
print('ASH_ORIGINAL_SURFACES_WRITTEN',len(records))
