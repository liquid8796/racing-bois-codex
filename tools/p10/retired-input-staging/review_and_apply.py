"""Validate the reviewed contextual client patch; write diff or apply only when explicitly requested."""
from pathlib import Path
import argparse,difflib,hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest-sha256',required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
raw=(HERE/'candidate-manifest.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=args.manifest_sha256:raise SystemExit('Reviewed manifest changed.')
manifest=json.loads(raw);diff=[]
for row in manifest['changes']:
    before=ROOT/row['path'];after=ROOT/row['staged'];actual=hashlib.sha256(before.read_bytes()).hexdigest() if before.exists() else None
    if not before.resolve().is_relative_to(ROOT) or not after.resolve().is_relative_to(HERE):raise SystemExit('Unsafe path.')
    if actual!=row['before'] or hashlib.sha256(after.read_bytes()).hexdigest()!=row['after']:raise SystemExit('Source drift: '+row['path'])
    if row['path'].startswith('Assets/'):
        diff.extend(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True) if before.exists() else [],after.read_text(encoding='utf8').splitlines(True),fromfile='a/'+row['path'],tofile='b/'+row['path']))
if hashlib.sha256((ROOT/'ArtSource/Weapons/RB_Club.blend').read_bytes()).hexdigest()!='553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f':raise SystemExit('Protected Club mismatch.')
(ROOT/'docs/p10/retired-input-staging/review-client.diff').write_text(''.join(diff),encoding='utf8')
if args.apply:
    for row in manifest['changes']:
        path=ROOT/row['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/row['staged']).read_bytes())
    print('APPLIED',len(manifest['changes']),'reviewed client/test files. No server/wire/policy changes.')
else:print('PRECHECK_PASS',len(manifest['changes']),'files; diff written, no production changes.')
