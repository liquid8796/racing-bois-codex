"""Read-only bilinear texture-sampling comparison for proposed collar UV scales."""
from pathlib import Path
from PIL import Image
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[4]
centres = [(0.6313332319259644, 0.536803662776947), (0.7264918088912964, 0.5198155641555786), (0.7644104957580566, 0.5606490969657898)]
maps = list((ROOT / 'Assets/RacingBois/Art/P08/Golden/Ash/V3/Textures').glob('AshV3_Rubber_*.png'))


def bilinear(image, uv):
    x = uv[0] * image.width - .5
    y = (1 - uv[1]) * image.height - .5
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    values = [image.getpixel(((ix + dx) % image.width, (iy + dy) % image.height)) for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1)]]
    return [(1 - fy) * ((1 - fx) * values[0][c] + fx * values[1][c]) + fy * ((1 - fx) * values[2][c] + fx * values[3][c]) for c in range(4)]


rows = []
for path in maps:
    image = Image.open(path).convert('RGBA')
    for lod, centre in enumerate(centres):
        for radius in [.001, .002, .004, .008]:
            maximum = [0.] * 4
            squared = [0.] * 4
            count = 0
            for yi in range(-10, 11):
                for xi in range(-10, 11):
                    x, y = xi / 10, yi / 10
                    if abs(x) + abs(y) > 1:
                        continue
                    before = bilinear(image, (centre[0] + .0004 * x, centre[1] + .0004 * y))
                    after = bilinear(image, (centre[0] + radius * x, centre[1] + radius * y))
                    for c in range(4):
                        difference = abs(before[c] - after[c])
                        maximum[c] = max(maximum[c], difference)
                        squared[c] += difference ** 2
                    count += 1
            rows.append({'map': path.name, 'lod': lod, 'radius': radius, 'samples': count,
                         'maximumStoredByteChannelChange': maximum, 'rmsStoredByteChannelChange': [math.sqrt(v / count) for v in squared]})
report = {'scope': 'Read-only full-resolution bilinear samples in stored PNG channels. sRGB lighting, normal direction, mip/compression and actual visual acceptance are separate.',
          'mapHashes': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in maps}, 'rows': rows}
(ROOT / 'docs/p08/golden/ash/v7r1/uv-sampling-options.json').write_text(json.dumps(report, indent=2) + '\n')
for radius in [.001, .002, .004, .008]:
    print(radius, [(path.name, max(max(r['maximumStoredByteChannelChange']) for r in rows if r['radius'] == radius and r['map'] == path.name)) for path in maps])
