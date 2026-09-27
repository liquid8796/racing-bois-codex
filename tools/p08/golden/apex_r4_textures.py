"""R4 original finish maps with explicit linear reflectance / sRGB storage.

Numeric reflectance values below are linear-light values. Only base/emission
colors are sRGB encoded. Normals, metallic, smoothness and roughness are data.
No R2/R3 files or licensed reference pixels are read or modified.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'ArtSource/P08/Golden/Apex/V8/R4/Textures'
OUT.mkdir(parents=True, exist_ok=True)
SPECS = {
    'Apex_Pearl': (2048, (.70, .72, .735), 0, .25, 'paint'),
    'Apex_Graphite': (1024, (.040, .044, .050), 0, .40, 'powdercoat'),
    'Apex_Machined': (1024, (.55, .57, .60), .96, .28, 'metal'),
    'Apex_Rubber': (1024, (.012, .014, .016), 0, .64, 'rubber'),
    'Apex_Titanium': (1024, (.34, .31, .255), .95, .32, 'metal'),
    'Apex_Glass': (512, (.055, .062, .070), 0, .085, 'glass'),
    'Apex_Lamp': (512, (.70, .78, .88), 0, .15, 'lamp'),
    'Apex_Lens': (512, (.90, .94, .97), 0, .025, 'glass'),
    'Apex_RedLamp': (512, (.38, .006, .012), 0, .20, 'lamp'),
}

def encode_srgb(linear):
    return np.where(linear <= .0031308, linear * 12.92, 1.055 * np.power(linear, 1 / 2.4) - .055)

def save(name, field, values):
    path = OUT / f'{name}_{field}.png'
    Image.fromarray(np.round(np.clip(values, 0, 1) * 255).astype(np.uint8)).save(path)
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

rows = []
for name, (size, reflectance, metallic, roughness, finish) in SPECS.items():
    rng = np.random.default_rng(5170401)
    grain = rng.random((size, size), dtype=np.float32) - .5
    y = np.arange(size, dtype=np.float32)[:, None] / size
    variation = grain * (.012 if finish == 'rubber' else .004)
    rgb_linear = np.clip(np.asarray(reflectance)[None, None, :] * (1 + variation[:, :, None]), 0, 1)
    base = save(name, 'BaseColor', encode_srgb(rgb_linear))
    rough = np.full((size, size), roughness, dtype=np.float32)
    rough += grain * (.045 if finish in ('rubber', 'powdercoat') else .014)
    if finish == 'metal':
        rough += .012 * np.sin(y * np.pi * 2 * 256)
    normal = np.zeros((size, size, 3), dtype=np.float32)
    normal[:, :, 0:2] = .5
    normal[:, :, 2] = 1
    if finish in ('rubber', 'powdercoat'):
        height = grain * .012
        normal[:, :, 0] -= (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5
        normal[:, :, 1] -= (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * .5
    maps = {'baseColor': base, 'normal': save(name, 'Normal', normal),
            'metallicSmoothness': save(name, 'MetallicSmoothness', np.dstack((np.full_like(rough, metallic), np.ones_like(rough), np.zeros_like(rough), 1 - rough))),
            'roughness': save(name, 'Roughness', rough)}
    if finish == 'lamp':
        maps['emission'] = save(name, 'Emission', encode_srgb(rgb_linear))
    rows.append({'material': name, 'size': size, 'baseReflectanceLinear': reflectance,
                 'baseEncodedSrgb': encode_srgb(np.asarray(reflectance)).tolist(), 'metallicLinear': metallic,
                 'roughnessLinear': roughness, 'finish': finish, 'maps': maps})
report = {'schema': 1, 'colorStorage': 'sRGB encoded BaseColor and Emission; all other textures unencoded linear data',
          'scalarDepth': '8-bit PNG; no implicit 16-bit normalization or color transform',
          'reference': 'Locked apex-v2 concept; original authored finish maps, no licensed pixels',
          'calibration': {'linear18PercentEncoded': float(encode_srgb(np.asarray(.18))), 'expected8Bit': 118},
          'visualAccepted': False, 'materials': rows}
(OUT / 'surface-intent.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'materials': len(rows), 'files': sum(len(r['maps']) for r in rows), 'directory': str(OUT)}))
