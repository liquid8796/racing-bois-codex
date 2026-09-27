"""Bind validated P06 hero sources and imports, or reject stale delivery evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / 'docs/p06/hero'
DESTINATION = FOLDER / 'source-manifest.json'
EXPECTED = {'RB_P06_Motorcycle', 'RB_P06_Rider', 'RB_P06_TrafficCoupe',
            'RB_P06_TrafficVan', 'RB_P06_PoliceMotorcycle', 'RB_P06_PoliceRider'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_audit():
    receipt = json.loads((FOLDER / 'saved-sources-audit-mcp.json').read_text(encoding='utf8'))
    if receipt['result'].get('isError'):
        raise RuntimeError('Saved source audit failed')
    output = receipt['result']['structuredContent']['result']
    report, _ = json.JSONDecoder().raw_decode(output[output.index('{"passed":'):])
    expected_sources = EXPECTED - {'RB_P06_PoliceRider'}
    if not report['passed'] or {a['root'] for a in report['assets']} != expected_sources:
        raise RuntimeError('Saved source audit does not cover all five geometries')
    if any(not asset['passed'] or not asset['meshes'] or any(not mesh['passed'] for mesh in asset['meshes'])
           for asset in report['assets']):
        raise RuntimeError('One or more saved source meshes failed audit')
    return report


def validate_unity():
    receipt = json.loads((FOLDER / 'unity-validation.json').read_text(encoding='utf8'))
    if not receipt['passed'] or {a['name'] for a in receipt['assets']} != EXPECTED:
        raise RuntimeError('Final Unity validation must cover all six variants')
    if any(not a['passed'] for a in receipt['assets']):
        raise RuntimeError('A Unity variant failed validation')
    for name in ['RB_P06_Rider', 'RB_P06_PoliceRider']:
        poses = json.loads((FOLDER / (name + '-unity-poses.json')).read_text(encoding='utf8'))
        if not poses['passed'] or len(poses['clips']) != 12 or poses['checkedVertices'] <= 0:
            raise RuntimeError('Imported animation proof is incomplete: ' + name)
    return receipt


def bound_paths():
    paths = set()
    for directory in ['tools/p06/hero', 'ArtSource/P06/Hero', 'Assets/RacingBois/Art/P06/Hero',
                      'Assets/RacingBois/Prefabs/P06', 'Assets/RacingBois/Materials/P06', 'docs/p06/hero']:
        for path in (ROOT / directory).rglob('*'):
            if not path.is_file() or path == DESTINATION or path.suffix in ['.blend1', '.blend2', '.pyc'] or '__pycache__' in path.parts:
                continue
            if ('Prefabs' in path.parts or 'Materials' in path.parts) and not any(
                    token in path.name for token in ['Motorcycle', 'Rider', 'Traffic']):
                continue
            paths.add(path)
    for relative in ['Assets/RacingBois/Editor/P06HeroAssetBuilder.cs',
                     'Assets/RacingBois/Editor/P06HeroAssetBuilder.cs.meta',
                     'ArtSource/Concepts/P06/motorcycle-v1.png', 'ArtSource/Concepts/P06/rider-v1.png',
                     'ArtSource/Concepts/P06/patrol-v1.png', 'ArtSource/Concepts/P06/PROMPTS.md',
                     'ArtSource/Concepts/P03P04/coupe-concept-v1.png', 'ArtSource/Concepts/P03P04/van-concept-v1.png']:
        path = ROOT / relative
        if not path.exists():
            raise RuntimeError('Required hero dependency missing: ' + relative)
        paths.add(path)
    return sorted(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check current paths and hashes without rewriting evidence')
    args = parser.parse_args()
    audit = parse_audit()
    unity = validate_unity()
    if args.check:
        manifest = json.loads(DESTINATION.read_text(encoding='utf8'))
        current = {p.relative_to(ROOT).as_posix(): p for p in bound_paths()}
        expected = {f['path']: f for f in manifest['files']}
        if current.keys() != expected.keys():
            raise RuntimeError('Manifest paths changed: ' + str(sorted(current.keys() ^ expected.keys())))
        changed = [name for name, path in current.items()
                   if path.stat().st_size != expected[name]['bytes'] or digest(path) != expected[name]['sha256']]
        if changed:
            raise RuntimeError('Manifest hashes changed: ' + ', '.join(changed))
        print(f"PASS: {len(current)} hero files match delivery manifest")
        return

    summary = {'schema': 1, 'passed': True, 'sourceCount': len(audit['assets']),
               'meshCount': sum(len(a['meshes']) for a in audit['assets']),
               'receiptSha256': digest(FOLDER / 'saved-sources-audit-mcp.json'),
               'scope': audit['scope'], 'assets': []}
    for asset in audit['assets']:
        source = ROOT / 'ArtSource/P06/Hero' / (asset['root'] + '.blend')
        summary['assets'].append({'name': asset['root'], 'source': source.relative_to(ROOT).as_posix(),
                                  'sha256': digest(source), 'passed': asset['passed'], 'meshes': asset['meshes']})
    (FOLDER / 'source-audit-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf8')
    files = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)}
             for p in bound_paths()]
    report = {'schema': 2, 'passed': True, 'generatedUtc': datetime.now(timezone.utc).isoformat(),
              'unityVersion': unity['unityVersion'], 'geometryExports': 5, 'prefabVariants': 6,
              'policy': 'Concepts precede 3D authoring; newly authored geometry and maps; patrol variants declare geometry reuse.',
              'files': files}
    DESTINATION.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(f'{len(files)} files bound: {DESTINATION}')


if __name__ == '__main__':
    main()
