"""Collect actual MCP export reports; concepts and production bytes are hash-bound."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
assets_by_name={}
receipts=[]
superseded=[]
for path in sorted((ROOT/'docs/p08/art').glob('*-creation-mcp.json'),key=lambda p:(p.stat().st_mtime_ns,p.name)):
    receipt=json.loads(path.read_text(encoding='utf8'))
    if receipt['result'].get('isError'): raise RuntimeError('MCP error: '+str(path))
    texts=[b.get('text','') for b in receipt['result'].get('content',[]) if b.get('type')=='text']
    output='\n'.join(texts)
    marker=output.rfind('{"batch":')
    if marker<0: raise RuntimeError('MCP export receipt has no successful asset report: '+str(path))
    report,_=json.JSONDecoder().raw_decode(output[marker:])
    for asset in report['assets']:
        for key in ['concept','source','fbx']:
            p=ROOT/asset[key]
            if not p.is_file(): raise RuntimeError('Missing authored dependency '+str(p))
            asset[key+'Sha256']=sha(p)
        asset['conceptInspectedBeforeGeometry']=report['conceptFirst']
        asset['creationReceipt']=path.relative_to(ROOT).as_posix()
        if asset['name'] in assets_by_name:
            superseded.append({'name':asset['name'],'receipt':assets_by_name[asset['name']]['creationReceipt'],'replacementReceipt':asset['creationReceipt']})
        assets_by_name[asset['name']]=asset
    receipts.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path)})
assets=sorted(assets_by_name.values(),key=lambda a:a['name'])
report={'schema':1,'passed':False,'state':'exported-awaiting-independent-source-and-Unity-QA','assets':assets,'receipts':receipts,'supersededReceipts':superseded,
        'policy':'Only successfully exported originals count. Reused P06 meshes, rigs, clips and atlas materials are declared separately; no source-game content.'}
destination=ROOT/'Assets/RacingBois/Art/P08/ArtManifest.json'
destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(ROOT/'docs/p08/art/export-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(str(len(assets))+' production exports collected')
