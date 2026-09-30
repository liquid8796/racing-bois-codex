"""Bind actual local study artifacts; leave runtime/concept acceptance false."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]
DOC=ROOT/'docs/p08/golden/ash/v8'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def row(path):return dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path))
def native(filename,marker):
    envelope=json.loads((DOC/filename).read_text(encoding='utf-8'))
    if envelope['result'].get('isError'):raise ValueError('Native error receipt')
    text='\n'.join(block['text'] for block in envelope['result']['content'] if block['type']=='text')
    value=json.JSONDecoder().raw_decode(text.split(marker+' ',1)[1])[0]
    out=DOC/(Path(filename).stem+'.data.json')
    if out.exists():raise ValueError('Fresh flattened native data required')
    out.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    return value
def main():
    out=DOC/'jacket02-handoff.json'
    if out.exists():raise ValueError('Fresh frozen handoff required')
    before=native('before-renders.json','ASH_V8_BEFORE')
    first=native('jacket01-renders.json','ASH_V8_JACKET01_RENDERS')
    second=native('jacket02-renders.json','ASH_V8_JACKET02_RENDERS')
    preservation=native('saved-jacket02-verification.json','ASH_V8_SAVED_JACKET02')
    floor=native('fall-floor-jacket02.json','ASH_V8_JACKET02_FLOOR')
    assert preservation['passed'] and floor['nonpenetrationSamplesPassed'] and floor['actionAndFrameRestored']
    keys=['label','cameraLocation','cameraRotation','orthoScale','width','height','frame','action']
    assert [[{key:item[key] for key in keys} for item in value['rows']] for value in [before,first,second]].count([{key:item[key] for key in keys} for item in before['rows']])==3
    images=[]
    for value in [before,first,second]:
        for item in value['rows']:
            path=Path(item['path'])
            with Image.open(path) as image:assert image.size==(item['width'],item['height']);image.verify()
            images.append(row(path))
    protected={
      'ArtSource/P08/Golden/Ash/V7R2/RB_Golden_Ash_V7R2.blend':'6d689a5df0ddf9de97d249bd4f56fd8a4e7bba844af80fc44a11c54fd428dcd8',
      'ArtSource/P08/Golden/Ash/V7R2/RB_Golden_Ash_V7R2.blend1':'472b1c44108999a4fd634795885db3ccc7afbdc230e4fa7885b8e9bb97426bb0',
      'ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_PreEdit.blend':'6d689a5df0ddf9de97d249bd4f56fd8a4e7bba844af80fc44a11c54fd428dcd8',
      'ArtSource/Concepts/P08/Golden/ash-v2.png':'6fa1090e13547df14e578f0ac77504ae5722d99a031a09e5f575c2775f9ce7e6',
      'ArtSource/Weapons/RB_Club.blend':'553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f'}
    for path,expected in protected.items():assert sha(ROOT/path)==expected
    source=ROOT/'ArtSource/P08/Golden/Ash/V8'
    scripts=sorted((ROOT/'tools/p08/golden/ash_v8').glob('*.py'))
    receipts=[DOC/name for name in ['handshake.json','open-owned-02.json','actor-probe.json','clothing-probe-02.json','author-jacket01.json',
              'finish-jacket02.json','before-renders.json','jacket01-renders.json','jacket02-renders.json','saved-jacket02-verification.json','fall-floor-jacket02.json']]
    result=dict(schema=1,scope='Frozen bounded clothing study, retained before further tailoring. Numeric preservation passed; visual/reference fidelity not achieved.',
        candidate=row(source/'RB_Golden_Ash_V8_Jacket02.blend'),rejectedGlossyStudy=row(source/'RB_Golden_Ash_V8_Jacket01.blend'),
        preservedRenderState=row(source/'RB_Golden_Ash_V8_Jacket02_Rendered.blend'),protected=[row(ROOT/path) for path in protected],
        images=images,recipes=[row(path) for path in scripts],receipts=[row(path) for path in receipts],
        savedPreservation=preservation,lodFallMinimums=floor['lodMinimums'],fallSamples=145,
        materialScope='Shared cloth/leather-detail/thread finish includes trousers and gloves; geometry is bounded upper-garment folds only.',
        visualAccepted=False,runtimeReady=False,proceduralFinishRequiresBake=True,unityImported=False,fbxExported=False,
        review='Amber/charcoal finish improved; the jacket remains too smooth/inflated, so reference-driven tailoring/folds/collar geometry is next.')
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(handoffSha256=sha(out),candidateSha256=result['candidate']['sha256'],preservationPassed=True,visualAccepted=False)))
if __name__=='__main__':main()
