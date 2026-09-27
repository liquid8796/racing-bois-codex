"""Numerically pack baked PBR channels; no authored raster artwork is edited."""
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
for role in ['BootLeather','Rubber']:
    intermediate=ROOT/'ArtSource/P08/Golden/Ash/V3/BakeIntermediate'
    final=ROOT/'Assets/RacingBois/Art/P08/Golden/Ash/V3/Textures'
    metallic=np.asarray(Image.open(intermediate/f'AshV3_{role}_Metallic.png').convert('RGBA'))
    roughness=np.asarray(Image.open(intermediate/f'AshV3_{role}_Roughness.png').convert('RGBA'))
    ao=np.asarray(Image.open(final/f'AshV3_{role}_Occlusion.png').convert('RGBA'))
    packed=np.zeros_like(metallic);packed[:,:,0]=metallic[:,:,0];packed[:,:,1]=ao[:,:,0];packed[:,:,3]=255-roughness[:,:,0]
    path=final/f'AshV3_{role}_MetallicSmoothness.png';Image.fromarray(packed,'RGBA').save(path)
    print(path.relative_to(ROOT).as_posix())
