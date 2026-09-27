"""Read-only binary FBX UV audit, using float32 inputs and double edge arithmetic."""
from pathlib import Path
import array
import hashlib
import json
import itertools
import struct
import zlib

ROOT = Path(__file__).resolve().parents[4]


def parse(path):
    data = path.read_bytes()
    assert data.startswith(b'Kaydara FBX Binary  \x00\x1a\x00')
    version = struct.unpack_from('<I', data, 23)[0]
    header = struct.Struct('<QQQB' if version >= 7500 else '<IIIB')

    def prop(offset):
        code = chr(data[offset])
        offset += 1
        scalar = {'Y': 'h', 'C': '?', 'I': 'i', 'F': 'f', 'D': 'd', 'L': 'q'}
        if code in scalar:
            fmt = struct.Struct('<' + scalar[code])
            return fmt.unpack_from(data, offset)[0], offset + fmt.size
        if code in ['S', 'R']:
            size = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            value = data[offset:offset + size]
            return (value.decode('utf-8', 'replace') if code == 'S' else value), offset + size
        if code in 'fdilbc':
            length, encoding, size = struct.unpack_from('<III', data, offset)
            payload = data[offset + 12:offset + 12 + size]
            if encoding:
                assert encoding == 1
                payload = zlib.decompress(payload)
            result = array.array({'l': 'q', 'b': 'b', 'c': 'b'}.get(code, code))
            result.frombytes(payload)
            assert len(result) == length
            return result, offset + 12 + size
        raise ValueError('Unknown FBX property ' + repr(code))

    def node(offset):
        end, count, length, name_size = header.unpack_from(data, offset)
        if not end:
            return None, offset + header.size
        offset += header.size
        name = data[offset:offset + name_size].decode()
        offset += name_size
        properties = []
        for _ in range(count):
            value, offset = prop(offset)
            properties.append(value)
        children = []
        while offset < end:
            child, offset = node(offset)
            if child is None:
                break
            children.append(child)
        return {'name': name, 'properties': properties, 'children': children}, end

    roots = []
    offset = 27
    while offset + header.size < len(data):
        current, offset = node(offset)
        if current is None:
            break
        roots.append(current)
    return roots


def child(node, name):
    return next(n for n in node['children'] if n['name'] == name)


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def cross(points):
    a, b, c = points
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def audit(path):
    objects = next(n for n in parse(path) if n['name'] == 'Objects')
    meshes = []
    for mesh in objects['children']:
        if mesh['name'] != 'Geometry' or mesh['properties'][2] != 'Mesh':
            continue
        name = mesh['properties'][1].split('\x00')[0]
        positions = child(mesh, 'Vertices')['properties'][0]
        indices = child(mesh, 'PolygonVertexIndex')['properties'][0]
        uv_layer = child(mesh, 'LayerElementUV')
        assert child(uv_layer, 'MappingInformationType')['properties'][0] == 'ByPolygonVertex'
        assert child(uv_layer, 'ReferenceInformationType')['properties'][0] == 'IndexToDirect'
        uv = child(uv_layer, 'UV')['properties'][0]
        ui = child(uv_layer, 'UVIndex')['properties'][0]
        materials = child(child(mesh, 'LayerElementMaterial'), 'Materials')['properties'][0]
        faces = []
        face = []
        for loop, v in enumerate(indices):
            face.append((loop, -v - 1 if v < 0 else v))
            if v < 0:
                faces.append(face)
                face = []
        failures = []
        numerical = []
        minimum = 1.0
        triangles = 0
        nontri = 0
        alternative_failures = []
        for polygon, face in enumerate(faces):
            if len(face) != 3:
                nontri += 1
                for tri in itertools.combinations(face, 3):
                    points = [(f32(uv[ui[loop] * 2]), f32(uv[ui[loop] * 2 + 1])) for loop, _ in tri]
                    area = cross(points)
                    if abs(area) <= 1e-14:
                        alternative_failures.append({'polygon': polygon, 'material': materials[polygon] if len(materials) > 1 else materials[0],
                            'faceVertices': [v for _, v in face], 'vertices': [v for _, v in tri],
                            'uv': points, 'doubleCross': area,
                            'positions': [list(positions[v * 3:v * 3 + 3]) for _, v in tri]})
            for j in range(1, len(face) - 1):
                tri = [face[0], face[j], face[j + 1]]
                points = [(f32(uv[ui[loop] * 2]), f32(uv[ui[loop] * 2 + 1])) for loop, _ in tri]
                area = cross(points)
                a, b, c = points
                blender_area = f32(b[0] - a[0]) * f32(c[1] - a[1]) - f32(b[1] - a[1]) * f32(c[0] - a[0])
                minimum = min(minimum, abs(area))
                if abs(area) <= 1e-14:
                    row = {'polygon': polygon, 'triangle': triangles, 'material': materials[polygon] if len(materials) > 1 else materials[0],
                           'uvIndices': [ui[loop] for loop, _ in tri], 'uv': points, 'doubleCross': area,
                           'oldBlenderFloatEdgeCross': blender_area,
                           'vertices': [v for _, v in tri],
                           'positions': [list(positions[v * 3:v * 3 + 3]) for _, v in tri]}
                    failures.append(row)
                    if abs(blender_area) > 1e-14:
                        numerical.append(row)
                triangles += 1
        meshes.append({'name': name, 'vertices': len(positions) // 3, 'polygons': len(faces), 'triangles': triangles,
                       'nonTrianglePolygons': nontri, 'minimumDoubleCross': minimum,
                       'failures': failures, 'falsePassUsingOldFloatEdges': len(numerical),
                       'alternativeTriangulationFailures': alternative_failures})
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'meshes': meshes, 'scope': 'Read-only binary FBX. Nontriangle polygons use fan triangulation and require Blender/native confirmation.'}


if __name__ == '__main__':
    paths = ['Assets/RacingBois/Art/P08/Golden/Ash/V6/RB_Golden_Ash_V6.fbx',
             'Assets/RacingBois/Art/P08/Golden/Ash/V7/RB_Golden_Ash_V7.fbx']
    report = {'sources': [audit(ROOT / p) for p in paths]}
    output = ROOT / 'docs/p08/golden/ash/v7r1/binary-uv-diagnosis.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for source in report['sources']:
        print(source['path'])
        for mesh in source['meshes']:
            print(mesh['name'], 'triangles', mesh['triangles'], 'nontri', mesh['nonTrianglePolygons'],
                  'bad', len(mesh['failures']), 'oldFloatFalsePass', mesh['falsePassUsingOldFloatEdges'])
            print('alternative failures', len(mesh['alternativeTriangulationFailures']))
            print(json.dumps(mesh['failures'][:3]))
