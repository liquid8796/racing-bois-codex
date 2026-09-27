"""Guarded client-only patch application. Root coordinates completed runs and Unity idle first."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest-sha256',required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
raw=(HERE/'candidate-manifest.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=args.manifest_sha256:raise SystemExit('Reviewed candidate manifest changed.')
manifest=json.loads(raw)
for row in manifest['changes']:
    path=ROOT/row['path'];staged=ROOT/row['staged']
    if not path.resolve().is_relative_to(ROOT) or not staged.resolve().is_relative_to(HERE):raise SystemExit('Unsafe manifest path.')
    actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if actual!=row['before']:raise SystemExit('Production drift: '+row['path'])
    if hashlib.sha256(staged.read_bytes()).hexdigest()!=row['after']:raise SystemExit('Staged source drift: '+row['staged'])
server=json.loads((ROOT/'Build/OciStaging/p09-20260927-f/release.json').read_text())
for row in server['source']['files']:
    if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise SystemExit('Backend f source drift: '+row['path'])
if hashlib.sha256((ROOT/'ArtSource/Weapons/RB_Club.blend').read_bytes()).hexdigest()!='553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f':raise SystemExit('Protected Club mismatch.')
if args.apply:
    for row in manifest['changes']:
        path=ROOT/row['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/row['staged']).read_bytes())
    print('APPLIED',len(manifest['changes']),'reviewed client/test files. Backend/runtime/protocol unchanged. Fresh tests required.')
else:print('PRECHECK_PASS',len(manifest['changes']),'files; no writes. Backend f runtime source remains identical.')
