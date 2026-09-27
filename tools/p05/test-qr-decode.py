"""Development-only independent QR decode. No decoder/Python is shipped."""
from pathlib import Path
import sys
import json
import importlib.metadata
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'_local/p05-qa'))
import zxingcpp
results=[]
for case in json.loads((ROOT/'_local/p05-qr-matrices.json').read_text()):
    for scale in [4,6]:
        size=case['size']+8
        image=Image.new('L',(size,size),255)
        for y,row in enumerate(case['modules']):
            for x,dark in enumerate(row):
                if dark:image.putpixel((x+4,y+4),0)
        image=image.resize((size*scale,size*scale),Image.Resampling.NEAREST)
        for rotation in [0,90]:
            decoded=zxingcpp.read_barcodes(image.rotate(rotation,expand=True))
            passed=len(decoded)==1 and decoded[0].text==case['url']
            if not passed:raise RuntimeError('QR roundtrip failed for '+case['url'])
            results.append({'url':case['url'],'scale':scale,'rotation':rotation,'decoded':decoded[0].text,'passed':True})
receipt={'passed':True,'cases':len(results),'encoder':'Vendored Nayuki browser JavaScript','decoder':'zxing-cpp 2.3.0 independent C++ implementation','playerRuntimeNeedsDecoder':False,'results':results}
(ROOT/'docs/p05/lan/qr-roundtrip.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(results)}))
