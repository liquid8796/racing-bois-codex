"""Compare semantic animation/skin bindings and every triangle's original UV corners."""
from inspect_uv import ROOT, parse, child
from verify_triangulated_control import digest_node
import collections
import json


def normalize(name):
    return name.split('\x00')[0].replace('_RetainedBody.001', '_RetainedBody')


def load(path):
    roots = parse(path)
    objects = {n['properties'][0]: n for n in next(r for r in roots if r['name'] == 'Objects')['children']}
    parents = collections.defaultdict(list)
    children = collections.defaultdict(list)
    for connection in next(r for r in roots if r['name'] == 'Connections')['children']:
        kind, source, target, *property_name = connection['properties']
        parents[source].append((target, property_name))
        children[target].append((source, property_name))
    return objects, parents, children


def semantic(path):
    objects, parents, children = load(path)
    animation = {}
    skin = {}
    shapes = {}
    materials = {}
    def target_name(identity):
        node = objects[identity]
        name = normalize(node['properties'][1])
        if node['name'] == 'Deformer' and node['properties'][2] == 'BlendShapeChannel':
            blend, _ = parents[identity][0]
            mesh, _ = parents[blend][0]
            return normalize(objects[mesh]['properties'][1]) + '|' + name
        return name
    for identity, node in objects.items():
        if node['name'] == 'AnimationCurve':
            target, axis = next((i, p) for i, p in parents[identity] if objects[i]['name'] == 'AnimationCurveNode')
            model, component = next((i, p) for i, p in parents[target] if p)
            layer, _ = next((i, p) for i, p in parents[target] if objects[i]['name'] == 'AnimationLayer')
            stack, _ = next((i, p) for i, p in parents[layer] if objects[i]['name'] == 'AnimationStack')
            key = '|'.join([normalize(objects[stack]['properties'][1]), target_name(model), *component, *axis])
            assert key not in animation
            animation[key] = digest_node(node, root=True)
        if node['name'] == 'Deformer' and node['properties'][2] == 'Cluster':
            deform, _ = parents[identity][0]
            mesh, _ = parents[deform][0]
            bone, _ = next((i, p) for i, p in children[identity] if objects[i]['name'] == 'Model')
            key = normalize(objects[mesh]['properties'][1]) + '|' + normalize(objects[bone]['properties'][1])
            assert key not in skin
            skin[key] = digest_node(node, root=True)
        if node['name'] == 'Geometry' and node['properties'][2] == 'Shape':
            channel, _ = parents[identity][0]
            blend, _ = parents[channel][0]
            mesh, _ = parents[blend][0]
            key = normalize(objects[mesh]['properties'][1]) + '|' + normalize(node['properties'][1])
            shapes[key] = digest_node(node, root=True)
        if node['name'] == 'Model' and node['properties'][2] == 'Mesh':
            materials[normalize(node['properties'][1])] = [normalize(objects[i]['properties'][1]) for i, _ in children[identity] if objects[i]['name'] == 'Material']
    return {'animationChannels': animation, 'skinClusters': skin, 'shapeDeltas': shapes, 'orderedMaterialBindings': materials}


def mesh_data(path):
    objects, _, _ = load(path)
    result = {}
    for mesh in objects.values():
        if mesh['name'] != 'Geometry' or mesh['properties'][2] != 'Mesh':
            continue
        indices = child(mesh, 'PolygonVertexIndex')['properties'][0]
        layer = child(mesh, 'LayerElementUV')
        uv = child(layer, 'UV')['properties'][0]
        ui = child(layer, 'UVIndex')['properties'][0]
        mats = child(child(mesh, 'LayerElementMaterial'), 'Materials')['properties'][0]
        faces = []
        face = []
        for loop, index in enumerate(indices):
            face.append((-index - 1 if index < 0 else index, tuple(uv[ui[loop] * 2:ui[loop] * 2 + 2])))
            if index < 0:
                faces.append((face, mats[len(faces)] if len(mats) > 1 else mats[0]))
                face = []
        result[normalize(mesh['properties'][1])] = faces
    return result


def main():
    original = ROOT / 'Assets/RacingBois/Art/P08/Golden/Ash/V7/RB_Golden_Ash_V7.fbx'
    control = ROOT / '_local/p08-ash-v7r1-staging/triangulated-diagnostic.fbx'
    before = semantic(original)
    after = semantic(control)
    checks = {key: {'same': before[key] == after[key], 'count': len(before[key])} for key in before}
    assert all(row['same'] for row in checks.values())
    before_mesh = mesh_data(original)
    after_mesh = mesh_data(control)
    triangle_checks = []
    for name, faces in before_mesh.items():
        by_vertex = collections.defaultdict(set)
        for polygon, (face, _) in enumerate(faces):
            for vertex, _ in face:
                by_vertex[vertex].add(polygon)
        assigned = collections.Counter()
        failures = []
        for triangle, (face, material) in enumerate(after_mesh[name]):
            assert len(face) == 3
            candidates = set.intersection(*(by_vertex[vertex] for vertex, _ in face))
            matches = []
            for polygon in candidates:
                old_face, old_material = faces[polygon]
                if old_material == material and all(corner in old_face for corner in face):
                    matches.append(polygon)
            if len(matches) != 1:
                failures.append({'triangle': triangle, 'matches': matches})
            else:
                assigned[matches[0]] += 1
        incomplete = [i for i, (face, _) in enumerate(faces) if assigned[i] != len(face) - 2]
        triangle_checks.append({'mesh': name, 'triangles': len(after_mesh[name]), 'cornerOrMaterialFailures': failures,
                                'incompleteOriginalPolygons': incomplete})
    assert all(not row['cornerOrMaterialFailures'] and not row['incompleteOriginalPolygons'] for row in triangle_checks)
    report = {'passed': True, 'semanticBindings': checks, 'triangleCornerChecks': triangle_checks,
              'scope': 'Exact connection-bound animation curves, skin weights/transforms, shape deltas, material ordering, and original polygon UV corner membership. Native importer/render still separate.'}
    (ROOT / 'docs/p08/golden/ash/v7r1/triangulated-semantic-preservation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'semanticBindings': checks, 'triangles': sum(row['triangles'] for row in triangle_checks)}))


if __name__ == '__main__':
    main()
