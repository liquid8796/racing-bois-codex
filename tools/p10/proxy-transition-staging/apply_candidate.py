"""Apply a reviewed candidate with whole-manifest hash guards. Does not stop any process."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest-sha256',required=True)
parser.add_argument('--apply',action='store_true')
args=parser.parse_args()
manifest_path=HERE/'candidate-manifest.json';raw=manifest_path.read_bytes()
if hashlib.sha256(raw).hexdigest()!=args.manifest_sha256:raise SystemExit('Reviewed manifest hash changed.')
manifest=json.loads(raw);changes=manifest['changes']
club=ROOT/'ArtSource/Weapons/RB_Club.blend'
if hashlib.sha256(club.read_bytes()).hexdigest()!='553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f':raise SystemExit('Protected Club hash mismatch; stop.')
for row in changes:
    path=ROOT/row['path'];stage=ROOT/row['staged']
    if not path.resolve().is_relative_to(ROOT) or not stage.resolve().is_relative_to(HERE):raise SystemExit('Unsafe manifest path.')
    actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if actual!=row['before']:raise SystemExit('Production drift: '+row['path'])
    if hashlib.sha256(stage.read_bytes()).hexdigest()!=row['after']:raise SystemExit('Staged drift: '+row['staged'])
if not args.apply:
    print('PRECHECK_PASS',len(changes),'files; no writes. Root must coordinate source-bound run supersession before --apply.')
else:
    for row in changes:
        path=ROOT/row['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/row['staged']).read_bytes())
    print('APPLIED',len(changes),'reviewed files. No processes stopped; fresh production regression is required.')
