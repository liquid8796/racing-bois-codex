"""Independently fingerprint exported geometry across authoring-only changes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('fbx_reader',ROOT/'docs/p08/review-2026-09-26/inspect_fbx_uv_readonly.py')
reader=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
fbx=ROOT/'Assets/RacingBois/Art/P08/Golden/Apex/RB_Golden_Apex.fbx'
objects=next(node[2] for node in reader.read_fbx(fbx) if node[0]=='Objects')
geometry=sorted((node[1][1],node[2]) for node in objects if node[0]=='Geometry')
models=sorted((node[1][1],node[1][2],node[2]) for node in objects if node[0]=='Model')
sha=hashlib.sha256(json.dumps([geometry,models],sort_keys=True,separators=(',',':')).encode()).hexdigest()
report={'runtimeGeometryAndTransformsSha256':sha,'fbxSha256':hashlib.sha256(fbx.read_bytes()).hexdigest(),'scope':'All exported geometry arrays, layers and model properties; excludes FBX creation IDs and timestamp, includes visible mesh transforms.'}
evidence=ROOT/'docs/p08/golden/apex'
if '--record-renders' in sys.argv:
    report['renders']=[{'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(evidence.glob('apex-*.png'))]
    (evidence/'rendered-geometry-signature.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
else:
    previous=json.loads((evidence/'rendered-geometry-signature.json').read_text(encoding='utf8'))
    report['matchesRenderedGeometry']=sha==previous['runtimeGeometryAndTransformsSha256']
    report['rendersUnchanged']=all(hashlib.sha256((ROOT/file['path']).read_bytes()).hexdigest()==file['sha256'] for file in previous['renders'])
    if not report['matchesRenderedGeometry'] or not report['rendersUnchanged']:raise SystemExit('Runtime geometry or renders changed; rerender this revision.')
    (evidence/'final-geometry-signature.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report))
