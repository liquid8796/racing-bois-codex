"""Apply only the hash-verified staged immunity patch after the root Unity-idle handoff."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3]
manifest=json.loads((Path(__file__).resolve().parent/'staged/manifest.json').read_text(encoding='utf8'))
if sys.argv[1:]!=['--root-confirmed-unity-idle']:raise SystemExit('Explicit root Unity-idle handoff required for this coordinated script write.')
for item in manifest:
    path=ROOT/item['path'];staged=ROOT/item['staged']
    current=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if current!=item['before']:raise SystemExit('Production file changed since staging: '+item['path'])
    if hashlib.sha256(staged.read_bytes()).hexdigest()!=item['after']:raise SystemExit('Staged content changed: '+item['staged'])
for item in manifest:
    path=ROOT/item['path'];path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((ROOT/item['staged']).read_bytes())
print('Applied6 hash-verified immunity files; source requires fresh compile/testing.')
