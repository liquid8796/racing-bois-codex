"""Map native collapsed triangles to unchanged FBX vertices/polygons."""
from inspect_uv import ROOT, parse, child
import collections
import itertools
import json
import math

native = json.loads((ROOT / 'docs/p08/golden/ash/v7r1/unity-collapsed-uv-triangles.json').read_text())
objects = next(n for n in parse(ROOT / 'Assets/RacingBois/Art/P08/Golden/Ash/V7/RB_Golden_Ash_V7.fbx') if n['name'] == 'Objects')
meshes = [n for n in objects['children'] if n['name'] == 'Geometry' and n['properties'][2] == 'Mesh']
rows = []
for level, mesh in enumerate(meshes):
    renderer = 'AshV7_L' + str(level) + '_Skin'
    failures = [n for n in native if n['renderer'] == renderer]
    positions = child(mesh, 'Vertices')['properties'][0]
    indices = child(mesh, 'PolygonVertexIndex')['properties'][0]
    layer = child(mesh, 'LayerElementUV')
    uv = child(layer, 'UV')['properties'][0]
    ui = child(layer, 'UVIndex')['properties'][0]
    faces = []
    face = []
    for loop, value in enumerate(indices):
        face.append((loop, -value - 1 if value < 0 else value))
        if value < 0:
            faces.append(face)
            face = []
    by_position = collections.defaultdict(list)
    for vertex in range(len(positions) // 3):
        x, y, z = positions[vertex * 3:vertex * 3 + 3]
        by_position[tuple(math.floor(v * 10000) for v in (x, y, -z))].append(vertex)
    mappings = []
    for native_row in failures:
        candidates = []
        for point in native_row['positions']:
            base = tuple(math.floor(v * 10000) for v in point)
            group = []
            for delta in itertools.product((-1, 0, 1), repeat=3):
                for vertex in by_position[tuple(base[a] + delta[a] for a in range(3))]:
                    actual = [positions[vertex * 3], positions[vertex * 3 + 1], -positions[vertex * 3 + 2]]
                    if max(abs(actual[a] - point[a]) for a in range(3)) <= 0.000001:
                        group.append(vertex)
            candidates.append(group)
        polygons = []
        for polygon, face in enumerate(faces):
            vertices = {v for _, v in face}
            if all(any(v in vertices for v in group) for group in candidates):
                polygons.append({'polygon': polygon, 'vertices': [v for _, v in face],
                    'uv': [list(uv[ui[loop] * 2:ui[loop] * 2 + 2]) for loop, _ in face]})
        mappings.append({'nativeTriangle': native_row['triangle'], 'nativeUv': native_row['uvs'],
                         'sourceCandidates': candidates, 'sourcePolygons': polygons})
    rows.append({'renderer': renderer, 'collapsedTriangles': len(failures), 'mappings': mappings})
report = {'scope': 'Exact frozen FBX position correspondence, native local Z sign inversion; no model writes.',
          'rows': rows}
(ROOT / 'docs/p08/golden/ash/v7r1/native-source-mapping.json').write_text(json.dumps(report, indent=2) + '\n')
for row in rows:
    print(row['renderer'], row['collapsedTriangles'], 'mapped', sum(bool(m['sourcePolygons']) for m in row['mappings']))
    print(json.dumps(row['mappings'][:1]))
