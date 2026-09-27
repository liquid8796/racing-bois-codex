"""Freeze current review evidence without touching Assets or earlier manifests."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location('canyon05_publication', SCRIPT.with_name('publish_candidate05.py'))
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
handoff = publisher.check()
destination = publisher.DOC/'candidate05-freeze-manifest.json'
if destination.exists():
    raise RuntimeError('Frozen evidence already exists; never regenerate in place.')

files = [publisher.ROOT/publisher.SOURCE, publisher.ROOT/publisher.FBX]
files.extend(path for path in publisher.DOC.iterdir() if path.is_file() and path != destination)
files.extend(SCRIPT.parent.glob('*.py'))
files = sorted(set(files))
intermediates = sorted(path for path in (publisher.ROOT/publisher.SOURCE).parent.iterdir()
    if path.is_file() and path not in files)
manifest = {
    'schema': 1, 'frozenUtc': datetime.now(timezone.utc).isoformat(),
    'reviewOnly': True, 'visualAccepted': False, 'productionMasksExpected': [1,1,1],
    'scope': 'Frozen Canyon05 source/FBX/render and bounded art/UV evidence. Native Unity import and final visual acceptance are separate.',
    'publicationHandoff': publisher.row(publisher.HANDOFF),
    'publicationArtifacts': [publisher.row(path) for path in files],
    'localIntermediateSources': [publisher.row(path) for path in intermediates],
    'localIntermediateScope': 'Retained local before-variant sources. Root may publish only05 source/FBX and all comparison renders/evidence/scripts; no intermediate is overwritten or deleted.',
    'protectedInputsVerified': [{'path': path, 'sha256': value} for path,value in publisher.LOCKED.items()],
    'nativeUnityResultIncluded': False,
}
with destination.open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
print(json.dumps({'manifest': publisher.row(destination), 'publicationArtifactCount': len(files),
                  'localIntermediateCount': len(intermediates), 'visualAccepted': False}, indent=2))
