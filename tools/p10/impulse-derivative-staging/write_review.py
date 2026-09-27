"""Write the exact three Application diffs after validating the frozen before/after hashes."""
from pathlib import Path
import difflib,hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
manifest=json.loads((HERE/'candidate-manifest.json').read_text());parts=[]
for row in manifest['changes']:
    if not row['path'].startswith('Assets/'):continue
    before=ROOT/row['path'];after=ROOT/row['staged']
    assert hashlib.sha256(before.read_bytes()).hexdigest()==row['before']
    assert hashlib.sha256(after.read_bytes()).hexdigest()==row['after']
    parts.extend(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),after.read_text(encoding='utf8').splitlines(True),fromfile='a/'+row['path'],tofile='b/'+row['path']))
out=ROOT/'docs/p10/impulse-derivative-staging/review-3-app-files.diff'
out.write_text(''.join(parts),encoding='utf8');print(out)
