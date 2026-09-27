"""Bind concept-guided club art and its actual validation receipts."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/p04/club'

def record(path):
    data=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

receipt=json.loads((OUT/'independent-geometry-uv-audit.json').read_text(encoding='utf-8'))
block=next(item['text'] for item in receipt['result']['content'] if item['type']=='text')
audit=json.loads(block[block.index('{'):])
if not audit['passed'] or len(audit['lods'])!=3:
    raise RuntimeError('Club independent geometry/UV audit did not pass')
paths=[ROOT/'ArtSource/Concepts/P03P04/club-concept-v1.png',ROOT/'ArtSource/Weapons/RB_Club.blend',
       ROOT/'Assets/RacingBois/Editor/ClubAssetBuilder.cs',OUT/'club-render.png',
       OUT/'blender-receipt.json',OUT/'independent-geometry-uv-audit.json',OUT/'ASSET.md',
       OUT/'unity-left-attack.png',OUT/'unity-right-attack.png']
for pattern in ['*.fbx','*.png','*.meta']:
    paths.extend(sorted((ROOT/'Assets/RacingBois/Art/Weapons/Club').glob(pattern)))
paths.extend(sorted((ROOT/'tools/p04/club').glob('*.py')))
unity_path=OUT/'unity-validation.json'
unity=None
if unity_path.exists():
    unity=json.loads(unity_path.read_text(encoding='utf-8'))
    if not unity.get('passed'):raise RuntimeError('Unity club validation did not pass')
    paths.extend([unity_path,ROOT/'Assets/RacingBois/Prefabs/RB_Club.prefab',ROOT/'Assets/RacingBois/Materials/RB_Club.mat'])
manifest={'generated_utc':datetime.now(timezone.utc).isoformat(),'asset':'RB_Club',
          'authorship':'Original Blender procedural geometry and PBR maps following inspected 2D concept; no original-game content',
          'blender_audit_passed':True,'unity_audit_passed':unity is not None,
          'lod_triangles':[lod['triangles'] for lod in audit['lods']],
          'attachment':{'root_identity':True,'shaft_axis':'+Y','grip':[0,0,0],'tip':[0,.475,0],'butt':[0,-.075,0]},
          'files':[record(path) for path in paths]}
(OUT/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(paths),'blender_passed':True,'unity_passed':unity is not None}))
