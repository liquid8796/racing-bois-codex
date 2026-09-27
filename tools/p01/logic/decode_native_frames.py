"""Decode captured native 8-bit frame buffers using captured DirectDraw palette."""
import json
from pathlib import Path
from native_project import OUT
from PIL import Image

records=[]
for meta in sorted((OUT/'native-frames').rglob('tick-*.json')):
    m=json.loads(meta.read_text())
    assert m['bpp']==8 and len(m['palette'])==1024
    raw=meta.with_suffix('.bin').read_bytes()
    assert len(raw)==m['pitch']*m['height']
    pixels=b''.join(raw[i*m['pitch']:i*m['pitch']+m['width']] for i in range(m['height']))
    im=Image.frombytes('P',(m['width'],m['height']),pixels)
    im.putpalette([v for i,v in enumerate(m['palette']) if i%4!=3])
    output=meta.with_suffix('.png');im.convert('RGB').save(output)
    records.append({'tick':m['tick'],'png':str(output.relative_to(OUT)),'unique_palette_indices':len(set(pixels))})
(OUT/'native-frames/index.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
