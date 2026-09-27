"""Create only V13 paint inputs; frozen V12 material files remain unchanged."""
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
base=ROOT/'Assets/RacingBois/Art/P08/Golden/Canyon/Textures'
out=ROOT/'Assets/RacingBois/Art/P08/Golden/Canyon/V13/Textures'
out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(704812)
asphalt=np.asarray(Image.open(base/'Canyon_Asphalt_BaseColor.png').resize((512,512),Image.Resampling.LANCZOS)).astype(float)
for name in ['Canyon_YellowPaint','Canyon_WhitePaint']:
    paint=np.asarray(Image.open(base/(name+'_BaseColor.png'))).astype(float)
    coarse=np.asarray(Image.fromarray(rng.integers(0,255,(48,48),dtype=np.uint8)).resize((512,512),Image.Resampling.BICUBIC)).astype(float)/255
    worn=(coarse<.45)&(rng.random((512,512))<.62)
    faded=paint*(.79+coarse[:,:,None]*.25)
    faded[worn]=asphalt[worn]*.9
    Image.fromarray(np.clip(faded,0,255).astype(np.uint8),'RGB').save(out/(name+'_BaseColor.png'))
print('CANYON_V13_PAINT_INPUTS 2; original V12 maps untouched')
