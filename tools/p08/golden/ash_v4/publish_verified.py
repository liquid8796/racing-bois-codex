"""Publish frozen V4 art bytes only. No Unity invocation or production acceptance."""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import uuid

PROJECT = Path(__file__).resolve().parents[4]
DOC = PurePosixPath('docs/p08/golden/ash/v4')
DEST = PurePosixPath('Assets/RacingBois/Art/P08/Golden/Ash/V4')
STAGING = PurePosixPath('_local/p08-ash-v4-publisher')
ROLES = ('Skin', 'LeatherDetails', 'TailoredLeather', 'HelmetEnamel', 'Forelocks')
CHANNELS = ('BaseColor', 'Normal', 'MetallicSmoothness', 'Occlusion')

@dataclass(frozen=True)
class Pins:
    delivery: str
    descriptor: str

FROZEN = Pins('e5f8e01279da1b8b2c36fa82dacee1df6d5f35845ecf0475a9a6630df1459a8a',
              '2d721c321d34b56a3030e1debaab63f205a2d0db35ddaa4ba764a2fae78c6d47')

class PublishError(RuntimeError):
    pass

def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def safe_path(root: Path, relative: str | PurePosixPath) -> Path:
    relative = PurePosixPath(str(relative))
    if relative.is_absolute() or not relative.parts or any(p in ('..', '.') or ':' in p or '\\' in p for p in relative.parts):
        raise PublishError('noncanonical_relative_path')
    value = root.joinpath(*relative.parts)
    resolved = value.resolve()
    if not resolved.is_relative_to(root) or resolved != value:
        raise PublishError('path_escape_or_link')
    return value

def verify_ref(root: Path, value: dict) -> None:
    path = safe_path(root, value['path'])
    expected = value['sha256']
    if not isinstance(expected, str) or len(expected) != 64 or not path.is_file() or digest(path) != expected.lower():
        raise PublishError('input_hash_mismatch:' + str(value['path']))

def references(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and 'sha256' in value:
            yield value
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)

def read_pinned(root: Path, relative: PurePosixPath, expected: str):
    path = safe_path(root, relative)
    if not path.is_file() or digest(path) != expected:
        raise PublishError('frozen_manifest_changed:' + str(relative))
    return json.loads(path.read_text(encoding='utf-8-sig'))

def preflight(root: Path, pins: Pins):
    delivery = read_pinned(root, DOC / 'delivery.json', pins.delivery)
    descriptor = read_pinned(root, DOC / 'descriptor-staged.json', pins.descriptor)
    if delivery.get('visualAccepted') is not False or delivery.get('nativeUnityVerified') is not False:
        raise PublishError('unexpected_acceptance_state')
    wanted = {f'AshV4_{role}_{channel}.png' for role in ROLES for channel in CHANNELS}
    textures = delivery['newTextures']
    if len(textures) != 20 or {PurePosixPath(t['path']).name for t in textures} != wanted:
        raise PublishError('unexpected_texture_set')
    if delivery['fbx']['path'] != '_local/p08-ash-v4-staging/RB_Golden_Ash_V4.fbx':
        raise PublishError('unexpected_fbx_source')
    for item in list(references(delivery)) + list(references(descriptor)):
        verify_ref(root, item)
    outputs = [(delivery['fbx'], DEST / 'RB_Golden_Ash_V4.fbx')]
    outputs.extend((item, DEST / 'Textures' / PurePosixPath(item['path']).name) for item in textures)
    mapping = {source['path']: str(target) for source, target in outputs}
    def rebind(value):
        if isinstance(value, dict):
            result = {k: rebind(v) for k, v in value.items()}
            if result.get('path') in mapping:
                result['path'] = mapping[result['path']]
            return result
        return [rebind(v) for v in value] if isinstance(value, list) else value
    published = rebind(descriptor)
    published['purpose'] = 'Isolated Ash V4 technical review. Art bytes published with verified hashes; native/visual/performance acceptance remains open. MenuHero is separate from the12 gameplay clips.'
    encoded = (json.dumps(published, indent=2) + '\n').encode('utf-8')
    descriptor_path = safe_path(root, DOC / 'descriptor.json')
    if descriptor_path.exists() and descriptor_path.read_bytes() != encoded:
        raise PublishError('existing_descriptor_conflict')
    target_paths = {safe_path(root, relative) for _, relative in outputs}
    target_root = safe_path(root, DEST)
    allowed = target_paths | {Path(str(p) + '.meta') for p in target_paths} | {target_root / 'Textures.meta'}
    if target_root.exists():
        for entry in target_root.rglob('*'):
            safe_path(root, entry.relative_to(root).as_posix())
            if entry.is_file() and entry not in allowed:
                raise PublishError('unrelated_file_in_destination')
    for source, relative in outputs:
        target = safe_path(root, relative)
        if target.exists() and (not target.is_file() or digest(target) != source['sha256']):
            raise PublishError('destination_hash_conflict:' + str(relative))
    return outputs, encoded

def create_file_no_replace(root: Path, target: Path, source: Path | bytes, expected_sha256: str) -> bool:
    if target.exists():
        return False  # Every existing output was verified in preflight and is checked again below.
    target.parent.mkdir(parents=True, exist_ok=True)
    safe_path(root, target.relative_to(root).as_posix())
    stage = safe_path(root, STAGING)
    stage.mkdir(parents=True, exist_ok=True)
    temporary = stage / (uuid.uuid4().hex + '.payload')
    try:
        if isinstance(source, bytes):
            with temporary.open('xb') as stream:
                stream.write(source)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            shutil.copyfile(source, temporary)
        if digest(temporary) != expected_sha256:
            raise PublishError('source_changed_before_publish')
        # Hard-link creation is atomic and fails if target appeared meanwhile.
        # Temporary data is a separate copied file, never a link to immutable input.
        os.link(temporary, target)
        return True
    finally:
        if temporary.exists():
            safe_path(root, temporary.relative_to(root).as_posix()).unlink()

def publish(root: Path = PROJECT, pins: Pins = FROZEN, verify_only: bool = False) -> dict:
    root = root.resolve()
    outputs, descriptor = preflight(root, pins)  # Complete validation before any mutation.
    existing = sum(safe_path(root, p).exists() for _, p in outputs)
    if verify_only:
        return {'passed': True, 'verifyOnly': True, 'plannedAssetFiles': len(outputs), 'existingVerifiedAssetFiles': existing}
    created = 0
    for source, relative in outputs:
        target = safe_path(root, relative)
        created += create_file_no_replace(root, target, safe_path(root, source['path']), source['sha256'])
        if digest(target) != source['sha256']:
            raise PublishError('postcopy_hash_mismatch:' + str(relative))
    preflight(root, pins)  # Recheck immutable inputs and all destinations before publishing descriptor.
    final_descriptor = safe_path(root, DOC / 'descriptor.json')
    descriptor_created = create_file_no_replace(root, final_descriptor, descriptor, hashlib.sha256(descriptor).hexdigest())
    if final_descriptor.read_bytes() != descriptor:
        raise PublishError('descriptor_postwrite_mismatch')
    preflight(root, pins)
    return {'passed': True, 'createdAssetFiles': created, 'reusedAssetFiles': len(outputs) - created,
            'descriptorCreated': descriptor_created, 'descriptor': str(DOC / 'descriptor.json'),
            'descriptorSha256': digest(final_descriptor), 'copiedFiles': [{'path': str(p), 'sha256': source['sha256']} for source, p in outputs],
            'sourceInputsRechecked': True, 'nativeUnityInvoked': False, 'visualAccepted': False, 'productionAcceptanceChanged': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    report = publish(verify_only=args.verify_only)
    report['publisherSha256'] = digest(Path(__file__))
    if not args.verify_only:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        path = safe_path(PROJECT.resolve(), DOC / 'publish-receipts' / (stamp + '.json'))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
        report['receipt'] = path.relative_to(PROJECT).as_posix()
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
