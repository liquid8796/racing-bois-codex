"""Read-only disk/source prerequisite inventory. Never creates Unity content or grants acceptance."""
from pathlib import Path
from collections import Counter
import datetime
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    with path.open('rb') as stream:
        value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
        return value.hexdigest()


def row(relative):
    path = ROOT / relative
    return {'path': relative, 'exists': path.is_file(), 'sha256': digest(path) if path.is_file() else None}


def audit():
    manifest_path = 'Assets/RacingBois/Art/P08/ArtManifest.json'
    manifest = json.loads((ROOT / manifest_path).read_text(encoding='utf-8'))
    entries = manifest['assets']
    declared = {entry['name']: entry for entry in entries}
    inputs = []
    for entry in entries:
        for field in ('concept', 'source', 'fbx'):
            item = row(entry[field]); item.update(asset=entry['name'], role=field, expectedSha256=entry.get(field + 'Sha256'))
            item['matchesDeclared'] = item['exists'] and item['sha256'] == item['expectedSha256']
            inputs.append(item)
    bike_source = (ROOT / 'Packages/com.racingbois.foundation/Runtime/Definitions/BikeCatalog.cs').read_text(encoding='utf-8')
    bike_names = {int(i): name for i, name in re.findall(r'new BikeDefinition\((\d+), "[^"]+", "([^"]+)"', bike_source)}
    rider_source = (ROOT / 'Packages/com.racingbois.foundation/Runtime/Definitions/CharacterCatalog.cs').read_text(encoding='utf-8')
    rider_names = {int(i): name for i, name in re.findall(r'new CharacterDefinition\((\d+),"[^"]+","([^"]+)"', rider_source)}
    bikes, riders = [], []
    for index in range(15):
        name = f'RB_P08_Bike_{index:02d}'
        bikes.append({'index': index, 'displayName': bike_names[index], 'semanticName': name, 'prefab': row('Assets/RacingBois/Prefabs/P08/' + name + '.prefab'),
                      'manifestEntry': name in declared, 'fbx': row('Assets/RacingBois/Art/P08/' + name + '.fbx'), 'source': row('ArtSource/P08/' + name + '.blend'),
                      'note': 'Existing slot00 is a P06 motorcycle prefab alias, not an accepted Golden Spark.' if index == 0 else 'Disk existence is not visual acceptance.'})
    for index in range(8):
        name = f'RB_P08_Rider_{index:02d}'
        riders.append({'index': index, 'displayName': rider_names[index], 'semanticName': name, 'prefab': row('Assets/RacingBois/Prefabs/P08/' + name + '.prefab'),
                       'fbx': row('Assets/RacingBois/Art/P08/' + name + '.fbx'), 'source': row('ArtSource/P08/' + name + '.blend'),
                       'portraits': [row(f'Assets/RacingBois/Art/P08/Portraits/RB_P08_Portrait_{index:02d}_{state:02d}.png') for state in range(3)]})
    generated = [row('Assets/RacingBois/Content/P08/' + name + '.asset') for name in ['Actors', 'Library', 'AudioBank', *['Route-' + str(i) for i in range(5)]]]
    props = [row('Assets/RacingBois/Prefabs/P08/' + entry['name'] + '.prefab') for entry in entries if entry['kind'] in {'scenery', 'landmark', 'foliage'}]
    p06 = ['RB_P06_RockA', 'RB_P06_RockB', 'RB_P06_Sage', 'RB_P06_DryGrass', 'RB_P06_Guardrail', 'RB_P06_Chevron', 'RB_P06_UtilityPole', 'RB_P06_PoliceMotorcycle', 'RB_P06_PoliceRider', 'RB_P06_TrafficCoupe', 'RB_P06_TrafficVan']
    legacy = [row('Assets/RacingBois/Prefabs/P06/' + name + '.prefab') for name in p06]
    legacy += [row(path) for path in ['Assets/RacingBois/Prefabs/RB_Pedestrian.prefab', 'Assets/RacingBois/Prefabs/RB_Club.prefab', 'Assets/RacingBois/Art/P06/Hero/RB_P06_Rider.fbx', 'Assets/RacingBois/Audio/P06/RB_P06_AudioBank.asset', 'Assets/RacingBois/Materials/RacePaint.mat', 'Assets/RacingBois/Materials/RaceYellow.mat', 'Assets/RacingBois/Materials/P06/RB_P06_Roadside.mat', 'Assets/RacingBois/Materials/P06/RB_P06_Asphalt.mat', 'Assets/RacingBois/Materials/P06/RB_P06_Gravel.mat']]
    surfaces = []
    for surface in sorted({entry['surface'] for entry in entries}):
        surfaces.append({'id': surface, 'material': row('Assets/RacingBois/Materials/P08/' + surface + '.mat'),
                         'maps': [row('Assets/RacingBois/Art/P08/' + surface + '_' + suffix + '.png') for suffix in ('BaseColor', 'Normal', 'MetallicSmoothness', 'Roughness')]})
    delivery = json.loads((ROOT / 'docs/p08/media/audio-delivery.json').read_text(encoding='utf-8'))
    audio = [dict(row(clip['oggPath']), id=clip['id'], category=clip['category'], role=clip['role'], expectedSha256=clip['oggSha256'], signalAuditPassed=clip['signalAuditPassed']) for clip in delivery['clips']]
    audio_bindings = [dict(row(delivery[name]), expectedSha256=delivery[name + 'Sha256']) for name in ('audioManifest', 'audioAudit')]
    ledger = json.loads((ROOT / 'docs/p08/content/ContentParityLedger.json').read_text(encoding='utf-8'))
    meta = (ROOT / 'Assets/RacingBois/Art/P06/Hero/RB_P06_Rider.fbx.meta').read_text(encoding='utf-8')
    proof_files = [manifest_path, 'Assets/RacingBois/Editor/P08ContentPackBuilder.cs', 'Assets/RacingBois/Editor/P08ArtBuilder.cs', 'Assets/RacingBois/Client/Presentation/P08ActorContent.cs', 'Assets/RacingBois/Client/Presentation/P08RouteContent.cs', 'Assets/RacingBois/Editor/GoldenProductionGate.cs', 'Assets/RacingBois/Editor/GoldenProductionBindings.cs', 'Packages/com.racingbois.foundation/Runtime/Definitions/ProductionContent.cs', 'docs/p08/content/ContentParityLedger.json', 'docs/p08/media/audio-delivery.json']
    production = (ROOT / 'Packages/com.racingbois.foundation/Runtime/Definitions/ProductionContent.cs').read_text(encoding='utf-8')
    masks = {kind: int(re.search(r'public const int ' + constant + r' = (\d+);', production)[1]) for kind, constant in [('route', 'AvailableRouteMask'), ('bike', 'AvailableBikeArtMask'), ('character', 'AvailableCharacterArtMask')]}
    return {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scope': 'Current read-only source/disk prerequisites; no Unity import, prefab creation, pack, native clip verification or visual acceptance.',
            'productionReady': False, 'generatedContent': generated, 'bikes': bikes, 'riders': riders, 'p08RouteProps': props, 'legacySupportingInputs': legacy,
            'surfaces': surfaces, 'routeMaterialsDirectoryExists': (ROOT / 'Assets/RacingBois/Materials/P08/Routes').exists(),
            'artManifestState': {'passed': manifest.get('passed'), 'state': manifest.get('state'), 'entryCount': len(entries), 'kinds': dict(Counter(entry['kind'] for entry in entries)), 'boundInputs': inputs},
            'audio': {'clips': audio, 'bindings': audio_bindings, 'categories': dict(Counter(clip['category'] for clip in delivery['clips'])), 'roles': dict(Counter(clip['role'] for clip in delivery['clips']))},
            'declaredP06ClipNames': re.findall(r'(?m)^\s+name: (RB_[A-Za-z]+)\s*$', meta),
            'promotionManifest': row('docs/p08/promotion/production-bindings.json'), 'goldenPrefabs': [row(path.relative_to(ROOT).as_posix()) for path in sorted((ROOT / 'Assets/RacingBois/Golden/Generated').rglob('*.prefab'))],
            'ledgerCoverage': ledger['coverage'], 'masks': masks,
            'distributionDirectories': {path: (ROOT / path).exists() for path in ['Build/Content-desktop', 'Build/Content-editor', 'Assets/StreamingAssets/Content']},
            'protectedClub': row('ArtSource/Weapons/RB_Club.blend'), 'auditSources': [row(path) for path in proof_files]}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a fresh audit artifact; existing evidence is preserved')
    result = audit(); args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2); stream.write('\n')
    print(json.dumps({'productionReady': False, 'missingGeneratedAssets': sum(not row['exists'] for row in result['generatedContent']), 'missingBikePrefabs': sum(not entry['prefab']['exists'] for entry in result['bikes']), 'missingRiderPrefabs': sum(not entry['prefab']['exists'] for entry in result['riders']), 'missingPortraits': sum(not row['exists'] for entry in result['riders'] for row in entry['portraits']), 'artHashMismatches': sum(not row['matchesDeclared'] for row in result['artManifestState']['boundInputs']), 'audioHashMismatches': sum(row['sha256'] != row['expectedSha256'] for row in result['audio']['clips'])}))
