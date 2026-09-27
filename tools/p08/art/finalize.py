"""Verify current asset bytes against the audited export manifest and Unity coverage."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--source-only',action='store_true');args=parser.parse_args()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def parse_result(path,marker):
    data=json.loads(path.read_text(encoding='utf8'))
    if data['result'].get('isError'):raise RuntimeError('MCP error: '+str(path))
    output='\n'.join(b.get('text','') for b in data['result']['content'] if b.get('type')=='text')
    return json.JSONDecoder().raw_decode(output[output.index(marker):])[0]
manifest_path=ROOT/'Assets/RacingBois/Art/P08/ArtManifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf8'))
audit_path=ROOT/'docs/p08/art/saved-sources-audit-mcp.json'
audit=parse_result(audit_path,'{"passed":')
expected={a['name'] for a in manifest['assets']}
if not audit['passed'] or {a['root'] for a in audit['assets']}!=expected:raise RuntimeError('Saved source QA coverage is incomplete.')
for asset in manifest['assets']:
    for key in ['source','fbx','concept']:
        if sha(ROOT/asset[key])!=asset[key+'Sha256']:raise RuntimeError('Post-audit asset dependency changed: '+asset[key])
summary={'passed':True,'sourceMeshCount':sum(len(a['meshes']) for a in audit['assets']),'exports':len(expected),
         'auditReceiptSha256':sha(audit_path),'sourceAudit':audit}
(ROOT/'docs/p08/art/source-audit-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
if args.source_only:
    print('PASS saved sources: '+str(len(expected))+' exports, '+str(summary['sourceMeshCount'])+' LOD meshes')
else:
    unity_path=ROOT/'docs/p08/art/unity-validation.json'
    unity=json.loads(unity_path.read_text(encoding='utf8'))
    if not unity['passed'] or {a['name'] for a in unity['assets']}!=expected or any(not a['passed'] for a in unity['assets']):raise RuntimeError('Unity asset QA coverage is incomplete.')
    paths=set()
    for folder in ['tools/p08/art','ArtSource/P08','Assets/RacingBois/Art/P08','Assets/RacingBois/Prefabs/P08','Assets/RacingBois/Materials/P08']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix not in ['.blend1','.blend2','.pyc'] and '__pycache__' not in p.parts:paths.add(p)
    for asset in manifest['assets']:paths.add(ROOT/asset['concept'])
    paths.update([ROOT/'Assets/RacingBois/Editor/P08ArtBuilder.cs',ROOT/'Assets/RacingBois/Editor/P08ArtBuilder.cs.meta',
                  ROOT/'tools/p06/hero/common.py',ROOT/'tools/p06/hero/audit.py',audit_path,unity_path])
    report={'schema':1,'passed':True,'exports':len(expected),'sourceMeshCount':summary['sourceMeshCount'],
            'geometryReuse':'Bike00 alias reuses original P06 Spark; rider identities reuse original P06 fifteen-bone rig and twelve clips. Reuse is excluded from new geometry/clip counts.',
            'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(paths)]}
    (ROOT/'docs/p08/art/source-manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('PASS source+UnityQA: '+str(len(expected))+' exports, '+str(len(paths))+' hash-bound files')
