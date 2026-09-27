"""Verify the separate radius-only FBX and prepare an unaccepted staged descriptor."""
from inspect_uv import ROOT, audit, parse, child, f32
from verify_export_connections import semantic, mesh_data
import hashlib
import json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry_without_uv(path):
    result = {}
    for parent in parse(path):
        if parent['name'] != 'Objects':
            continue
        for mesh in parent['children']:
            if mesh['name'] != 'Geometry' or mesh['properties'][2] != 'Mesh':
                continue
            result[mesh['properties'][1]] = {name: list(child(mesh, name)['properties'][0]) for name in ['Vertices', 'PolygonVertexIndex']}
    return result


def main():
    original = ROOT / 'Assets/RacingBois/Art/P08/Golden/Ash/V7/RB_Golden_Ash_V7.fbx'
    candidate = ROOT / '_local/p08-ash-v7r1-staging/RB_Golden_Ash_V7R1.fbx'
    source = ROOT / 'ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend'
    before = semantic(original)
    after = semantic(candidate)
    checks = {key: {'same': before[key] == after[key], 'count': len(before[key])} for key in before}
    assert all(row['same'] for row in checks.values())
    assert geometry_without_uv(original) == geometry_without_uv(candidate)
    old_meshes = mesh_data(original)
    new_meshes = mesh_data(candidate)
    centres = [(0.6313332319259644, 0.536803662776947), (0.7264918088912964, 0.5198155641555786), (0.7644104957580566, 0.5606490969657898)]
    uv_rows = []
    for level, name in enumerate(old_meshes):
        old_faces, new_faces = old_meshes[name], new_meshes[name]
        assert len(old_faces) == len(new_faces)
        changed = []
        for polygon, ((old_face, old_material), (new_face, new_material)) in enumerate(zip(old_faces, new_faces)):
            assert old_material == new_material and [v for v, uv in old_face] == [v for v, uv in new_face]
            for corner, ((vertex, old_uv), (_, new_uv)) in enumerate(zip(old_face, new_face)):
                if old_uv == new_uv:
                    continue
                assert old_material == 5, 'UV changed outside rubber material'
                expected = tuple(f32(centres[level][axis] + 5 * (old_uv[axis] - centres[level][axis])) for axis in range(2))
                assert new_uv == expected, 'UV change is not exactly authorised fivefold scale'
                changed.append({'polygon': polygon, 'corner': corner, 'vertex': vertex, 'before': old_uv, 'after': new_uv})
        assert len(changed) == 280 and len({row['polygon'] for row in changed}) == 70
        uv_rows.append({'mesh': name, 'changedLoops': len(changed), 'changedPolygons': 70, 'changes': changed})
    numerical = audit(candidate)
    assert all(not mesh['failures'] and not mesh['alternativeTriangulationFailures'] for mesh in numerical['meshes'])
    descriptor = json.loads((ROOT / 'docs/p08/golden/ash/v7/descriptor.json').read_text())
    descriptor['purpose'] = 'Unaccepted radius-only AshV7R1 native UV conversion control. New losslessly compressed source; frozen V7 preserved. No geometry/rig/animation/map edits; exact visual acceptance remains open.'
    asset = descriptor['assets'][0]
    asset['id'] = 'RB_Golden_Ash_V7R1'
    asset['source'] = {'path': source.relative_to(ROOT).as_posix(), 'sha256': sha(source)}
    asset['fbx'] = {'path': candidate.relative_to(ROOT).as_posix(), 'sha256': sha(candidate)}
    for clip in asset['clips'] + asset.get('previewClips', []):
        clip['path'] = asset['fbx']['path']
        clip['sha256'] = asset['fbx']['sha256']
    for material in asset['materials']:
        for value in material.values():
            if isinstance(value, dict) and 'path' in value and 'sha256' in value:
                assert sha(ROOT / value['path']) == value['sha256'], 'Bound material map changed'
    report = {'passed': True, 'source': asset['source'], 'fbx': asset['fbx'], 'sourceBytes': source.stat().st_size,
              'nativeCompressedSource': True, 'originalSourceSha256': sha(ROOT / 'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend'),
              'originalExportSha256': sha(original), 'geometryVerticesAndPolygonsExact': True, 'semanticBindings': checks,
              'uv': uv_rows, 'numericAudit': numerical, 'mapsUnchanged': True, 'nativePending': True, 'visualAccepted': False,
              'normalSamplingDifference': 'See uv-sampling-options.json radius0.002: up to7.740054 stored byte units at full-resolution bilinear sampling; native mip/compression/shading review remains required.'}
    (ROOT / 'docs/p08/golden/ash/v7r1/radius-candidate-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    (ROOT / 'docs/p08/golden/ash/v7r1/descriptor-radius-staged.json').write_text(json.dumps(descriptor, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['passed', 'source', 'fbx', 'sourceBytes', 'semanticBindings', 'geometryVerticesAndPolygonsExact', 'mapsUnchanged']}))


if __name__ == '__main__':
    main()
