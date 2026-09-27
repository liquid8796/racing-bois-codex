"""Original deterministic physical-surface maps, no extracted game imagery.

Full-field surfaces deliberately tile over manufactured parts at consistent
world density. These are not colour swatches or a material palette atlas.
"""
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Assets/RacingBois/Art/P08/Golden/Apex/V8/R2'
OUT.mkdir(parents=True, exist_ok=True)
SPEC = {
    'Apex_Pearl': (2048, (.76, .78, .79), .18, .25, 'paint'),
    'Apex_Graphite': (1024, (.045, .048, .052), .38, .38, 'cast'),
    'Apex_Machined': (1024, (.44, .46, .48), .94, .29, 'brushed'),
    'Apex_Rubber': (1024, (.014, .016, .018), .0, .66, 'rubber'),
    'Apex_Titanium': (1024, (.29, .26, .20), .94, .30, 'brushed'),
    'Apex_Glass': (512, (.035, .039, .045), .08, .12, 'glass'),
    'Apex_Lamp': (512, (.74, .82, .88), .12, .18, 'lens'),
    'Apex_Lens': (512, (.93, .95, .97), .0, .045, 'glass'),
    'Apex_RedLamp': (512, (.38, .004, .008), .08, .21, 'lens'),
}

for name, (size, colour, metallic, roughness, role) in SPEC.items():
    rng = np.random.default_rng(51703)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    u, v = x / size, y / size
    grain = rng.random((size, size), dtype=np.float32) - .5
    broad = np.sin(u * 2 * np.pi * 19 + np.sin(v * 2 * np.pi * 7))
    if role == 'brushed':
        height = .12 * np.sin(v * 2 * np.pi * 380) + grain * .04
        variation = grain * .025 + np.sin(v * 2 * np.pi * 380) * .025
    elif role == 'rubber':
        height = grain * .14 + np.sin(u * 2 * np.pi * 180) * .018
        variation = grain * .018 + broad * .003
    elif role == 'cast':
        height = grain * .10
        variation = grain * .018
    elif role == 'lens':
        height = np.sin(u * 2 * np.pi * 48) * .065
        variation = grain * .002
    else:
        height = grain * (.008 if role == 'paint' else .002)
        variation = grain * (.008 if role == 'paint' else .001)
    rgb = np.clip(np.asarray(colour)[None, None, :] + variation[:, :, None], 0, 1)
    Image.fromarray(np.round(rgb * 255).astype(np.uint8)).save(OUT / f'{name}_BaseColor.png')
    dx = np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)
    dy = np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)
    normal = np.dstack((-dx, -dy, np.ones_like(dx)))
    normal /= np.linalg.norm(normal, axis=2)[:, :, None]
    Image.fromarray(np.round((normal * .5 + .5) * 255).astype(np.uint8)).save(OUT / f'{name}_Normal.png')
    rough = np.clip(roughness + grain * (.08 if role in ('rubber', 'cast') else .025), 0, 1)
    mask = np.dstack((np.full_like(rough, metallic), np.ones_like(rough), np.zeros_like(rough), 1 - rough))
    Image.fromarray(np.round(mask * 255).astype(np.uint8)).save(OUT / f'{name}_MetallicSmoothness.png')
    Image.fromarray(np.round(rough * 255).astype(np.uint8)).save(OUT / f'{name}_Roughness.png')
    if role == 'lens':
        emission = rgb * (.32 if name == 'Apex_Lamp' else 1)
        Image.fromarray(np.round(emission * 255).astype(np.uint8)).save(OUT / f'{name}_Emission.png')
print('APEX_SURFACE_MAPS_WRITTEN', len(SPEC))
