"""Original UV paint following the locked copper/cream concept; no source pixels copied."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'ArtSource/P08/Golden/Spark/V1/Textures'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048

def smooth_loop(points, steps=20):
    result=[]
    for i in range(len(points)):
        a,b,c,d=[np.asarray(points[k%len(points)]) for k in [i-1,i,i+1,i+2]]
        for j in range(steps):
            t=j/steps
            result.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return [tuple(p*SIZE) for p in result]

u,v=np.meshgrid(np.arange(SIZE)/SIZE,np.arange(SIZE)/SIZE)
interior=np.zeros((SIZE,SIZE),dtype=bool)
cream=np.zeros((SIZE,SIZE),dtype=bool)
outline=np.zeros((SIZE,SIZE),dtype=bool)
dark=np.zeros((SIZE,SIZE),dtype=bool)
base_loop=[(.088,.361),(.068,.340),(.108,.261),(.259,.192),(.503,.155),(.724,.163),(.831,.199),(.865,.248),(.861,.302),(.829,.348),(.767,.376),(.346,.375)]
for mirror in [False,True]:
    points=[(x,1-y if mirror else y) for x,y in base_loop]
    image=Image.new('L',(SIZE,SIZE));draw=ImageDraw.Draw(image);path=smooth_loop(points)
    draw.polygon(path,fill=255);mask=np.asarray(image)>0;interior|=mask
    vv=1-v if mirror else v
    boundary=.591+.106*np.sin(np.clip((vv-.155)/.221,0,1)*np.pi)
    patch=mask&(u>boundary);cream|=patch
    dark|=mask&(np.abs(u-boundary)<.0032)
    image=Image.new('L',(SIZE,SIZE));draw=ImageDraw.Draw(image);draw.line(path+[path[0]],fill=255,width=12,joint='curve');dark|=np.asarray(image)>0
    image=Image.new('L',(SIZE,SIZE));draw=ImageDraw.Draw(image);draw.line(path+[path[0]],fill=255,width=5,joint='curve');outline|=np.asarray(image)>0

rng=np.random.default_rng(45001);grain=rng.random((SIZE,SIZE),dtype=np.float32)-.5
copper=np.asarray((.28,.065,.012));ivory=np.asarray((.66,.595,.475));ink=np.asarray((.012,.013,.014))
linear=np.broadcast_to(copper,(SIZE,SIZE,3)).copy();linear*=1+grain[:,:,None]*.018
linear[cream]=ivory;linear[dark]=ink;linear[outline]=ivory
encoded=np.where(linear<=.0031308,linear*12.92,1.055*np.power(linear,1/2.4)-.055)
Image.fromarray(np.round(np.clip(encoded,0,1)*255).astype(np.uint8)).save(OUT/'Spark_Copper_BaseColor.png')
rough=np.full((SIZE,SIZE),.23,dtype=np.float32)+grain*.016;rough[cream|outline]=.27
metal=np.full((SIZE,SIZE),.20,dtype=np.float32);metal[cream|dark|outline]=0
mask=np.dstack((metal,np.ones_like(metal),np.zeros_like(metal),1-rough))
Image.fromarray(np.round(mask*255).astype(np.uint8)).save(OUT/'Spark_Copper_MetallicSmoothness.png')
Image.fromarray(np.round(rough*255).astype(np.uint8)).save(OUT/'Spark_Copper_Roughness.png')
height=grain*.008
normal=np.dstack((-(np.roll(height,-1,1)-np.roll(height,1,1)),-(np.roll(height,-1,0)-np.roll(height,1,0)),np.ones_like(height)))
normal/=np.linalg.norm(normal,axis=2)[:,:,None]
Image.fromarray(np.round((normal*.5+.5)*255).astype(np.uint8)).save(OUT/'Spark_Copper_Normal.png')
files=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.glob('Spark_Copper_*.png'))]
(OUT/'tank-paint-intent.json').write_text(json.dumps({'originalPixels':True,'sourceImagePixelsCopied':False,'baseColorStorage':'sRGB encoded from linear reflectance','copperReflectanceLinear':[.28,.065,.012],'creamReflectanceLinear':[.66,.595,.475],'dataMaps':'linear unencoded','creamStripeBothFlanks':True,'files':files,'visualAccepted':False},indent=2)+'\n')
print('SPARK_TANK_PAINT_MAPS',len(files))
