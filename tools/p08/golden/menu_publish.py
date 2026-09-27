"""Publish exact frozen menu bytes idempotently; no Unity calls or acceptance."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import uuid

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / 'docs/p08/golden/menu-environment/v1'
TARGET = 'Assets/RacingBois/Art/P08/Golden/MenuEnvironment/V1/RB_Golden_MenuEnvironment.fbx'
STAGED_SHA = '5c47c11b8ae4c64aa74de665d41adb31688969d9f28eacfa09491efadba6a837'


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def safe(name):
    candidate = ROOT / name
    for part in [candidate, *candidate.parents]:
        if part == ROOT:
            break
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise RuntimeError('Refusing reparse-point publication path')
    path = candidate.resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise RuntimeError('Publication path outside project')
    return path


def check_inputs(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
            if digest(safe(value['path'])) != value['sha256']:
                raise RuntimeError('Frozen input changed: ' + value['path'])
        for child in value.values():
            check_inputs(child)
    elif isinstance(value, list):
        for child in value:
            check_inputs(child)


def publish_bytes(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError('Refusing to replace a different existing publication: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Stage complete bytes outside Assets, then atomically create the destination
    # with a hard link (no overwrite race). The resulting target is a normal file.
    temporary = safe('_local/p08-menu-environment-v1-staging/.publish-' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as stream:
            stream.write(data)
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise RuntimeError('Publication was concurrently replaced with different bytes')
    finally:
        temporary.unlink(missing_ok=True)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--publish', action='store_true')
    options = args.parse_args()
    descriptor = json.loads((DOC / 'descriptor-staged.json').read_text())
    mapping = json.loads((DOC / 'module-lod-mapping-staged.json').read_text())
    delivery = json.loads((DOC / 'delivery.json').read_text())
    check_inputs(descriptor); check_inputs(delivery)
    asset = descriptor['assets'][0]
    source = safe(asset['fbx']['path'])
    if digest(source) != STAGED_SHA:
        raise RuntimeError('Frozen final FBX differs')
    asset['fbx'] = {'path': TARGET, 'sha256': STAGED_SHA}
    mapping['source'] = asset['fbx']
    map_bytes = (json.dumps(mapping, indent=2) + '\n').encode()
    map_path = 'docs/p08/golden/menu-environment/v1/module-lod-mapping.json'
    asset['moduleLodMap'] = {'path': map_path, 'sha256': hashlib.sha256(map_bytes).hexdigest()}
    descriptor_bytes = (json.dumps(descriptor, indent=2) + '\n').encode()
    outputs = [(safe(TARGET), source.read_bytes()), (safe(map_path), map_bytes), (DOC / 'descriptor.json', descriptor_bytes)]
    for path, data in outputs:
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError('Existing destination differs; use a new version')
    if options.publish:
        for path, data in outputs:
            publish_bytes(path, data)
        check_inputs(descriptor)
    receipt = {'schema': 1, 'published': options.publish, 'visualAccepted': False, 'unityCalled': False,
               'sourceAndFbxFrozen': True, 'files': [{'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for path, data in outputs],
               'suggestedScenePlacementY': 0.02496814727783203,
               'scope': 'Verified exact file publication only; root owns native import/camera/contact/lighting review.'}
    if options.publish:
        publish_bytes(DOC / 'publication.json', (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
