"""Hash-guarded application of the reviewed native transport fix; no server/runtime-policy changes."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest-sha256',required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
raw=(HERE/'candidate-manifest.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=args.manifest_sha256:raise SystemExit('Reviewed manifest mismatch.')
manifest=json.loads(raw)
for row in manifest['changes']:
    path=ROOT/row['path'];staged=ROOT/row['staged']
    if not path.resolve().is_relative_to(ROOT) or not staged.resolve().is_relative_to(HERE):raise SystemExit('Unsafe path.')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=row['before']:raise SystemExit('Production drift: '+row['path'])
    if hashlib.sha256(staged.read_bytes()).hexdigest()!=row['after']:raise SystemExit('Staged drift: '+row['staged'])
if hashlib.sha256((ROOT/'ArtSource/Weapons/RB_Club.blend').read_bytes()).hexdigest()!='553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f':raise SystemExit('Protected Club hash mismatch.')
if args.apply:
    for row in manifest['changes']:(ROOT/row['path']).write_bytes((ROOT/row['staged']).read_bytes())
    print('APPLIED transport and permanent regression. Server/protocol/timeouts unchanged; native WSS verification required.')
else:print('PRECHECK_PASS; no writes. Wait for root coordinated Unity idle/apply approval.')
