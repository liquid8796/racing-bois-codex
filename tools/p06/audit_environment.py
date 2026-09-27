"""Read-only Blender audit for the concept-led P06 canyon source.

Run through the parent's live Blender MCP after create_environment.py completes.
No operator, mesh edit, transform edit, mode switch, save, or export is performed.
Only Blender's derived triangle cache is requested. JSON is printed for capture.
Connected components may reuse a material atlas intentionally; overlap within a
component must pass the exact clipped-triangle check or an explicit exception.
"""
import bpy
import json
import math
from collections import defaultdict

EXPECTED_BLEND = 'D:/Project/Unity/racing-bois/ArtSource/P06/Environment/RB_P06_CanyonKit.blend'
ASSETS = ('RockA', 'RockB', 'Sage', 'DryGrass', 'Guardrail', 'Chevron', 'UtilityPole')
UV_AREA_EPS = 1e-11
OVERLAP_AREA_EPS = 1e-10
GEOMETRY_AREA_EPS = 1e-10
MAX_PAIR_CHECKS_PER_MESH = 2_000_000
MAX_VERTICES_PER_MESH = 25000
MAX_TRIANGLES_PER_MESH = 50000
EXAMPLE_LIMIT = 12


def cross2(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def polygon_area(points):
    if len(points) < 3:
        return 0.0
    return abs(math.fsum(points[i][0]*points[(i+1) % len(points)][1] -
                         points[(i+1) % len(points)][0]*points[i][1]
                         for i in range(len(points)))) * .5


def triangle_intersection_area(subject, clip):
    """Sutherland-Hodgman convex clipping, independent of either UV winding."""
    points = list(subject)
    sign = 1 if cross2(clip[0], clip[1], clip[2]) >= 0 else -1
    for i in range(3):
        a, b = clip[i], clip[(i+1) % 3]
        if not points:
            return 0.0
        output = []
        previous = points[-1]
        dp = sign * cross2(a, b, previous)
        for current in points:
            dc = sign * cross2(a, b, current)
            previous_inside, current_inside = dp >= -1e-14, dc >= -1e-14
            if previous_inside != current_inside:
                divisor = dp-dc
                if abs(divisor) > 1e-20:
                    t = min(1.0, max(0.0, dp/divisor))
                    output.append((previous[0]+t*(current[0]-previous[0]),
                                   previous[1]+t*(current[1]-previous[1])))
            if current_inside:
                output.append(current)
            previous, dp = current, dc
        points = output
    return polygon_area(points)


def find(parents, value):
    while parents[value] != value:
        parents[value] = parents[parents[value]]
        value = parents[value]
    return value


def union(parents, first, second):
    a, b = find(parents, first), find(parents, second)
    if a != b:
        parents[b] = a


def allowed_sign_reuse(name, first, second):
    # The source explicitly declares reuse for opposite front/back board faces.
    # Side/bevel/front overlaps are not excused, and no other model has this rule.
    if 'Chevron' not in name:
        return False
    an, bn = first['normal'], second['normal']
    return abs(an[1]) >= .98 and abs(bn[1]) >= .98 and an[1]*bn[1] < -.96


def bounded_append(items, value):
    if len(items) < EXAMPLE_LIMIT:
        items.append(value)


def audit_mesh(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    if len(mesh.vertices) == 0 or len(mesh.polygons) == 0 or len(mesh.loop_triangles) == 0:
        return {'name': obj.name, 'vertices': len(mesh.vertices), 'faces': len(mesh.polygons),
                'triangles': len(mesh.loop_triangles), 'passed': False, 'auditComplete': True,
                'emptyMesh': True, 'failureReason': 'mesh_requires_vertices_faces_and_triangles'}
    if len(mesh.vertices) > MAX_VERTICES_PER_MESH or len(mesh.loop_triangles) > MAX_TRIANGLES_PER_MESH:
        return {'name': obj.name, 'passed': False, 'auditComplete': False,
                'boundedStopReason': 'source_size_budget'}
    parents = list(range(len(mesh.vertices)))
    for edge in mesh.edges:
        union(parents, edge.vertices[0], edge.vertices[1])
    component_vertices = defaultdict(list)
    for vertex in mesh.vertices:
        component_vertices[find(parents, vertex.index)].append(vertex.index)
    component_ids = {key: index for index, key in enumerate(sorted(component_vertices))}
    edge_faces = defaultdict(list)
    referenced = set()
    for polygon in mesh.polygons:
        vertices = list(polygon.vertices)
        referenced.update(vertices)
        for i in range(len(vertices)):
            a, b = vertices[i], vertices[(i+1) % len(vertices)]
            edge_faces[(min(a, b), max(a, b))].append((polygon.index, 1 if a < b else -1))
    non_manifold = sum(len(faces) != 2 for faces in edge_faces.values())
    inconsistent = sum(len(faces) == 2 and faces[0][1] == faces[1][1] for faces in edge_faces.values())
    loose_edges = sum(tuple(sorted(edge.vertices)) not in edge_faces for edge in mesh.edges)
    loose_vertices = len(mesh.vertices)-len(referenced)
    uv_layer = mesh.uv_layers.active
    result = {'name': obj.name, 'vertices': len(mesh.vertices), 'triangles': len(mesh.loop_triangles),
              'components': len(component_vertices), 'nonManifoldEdges': non_manifold,
              'inconsistentWindingEdges': inconsistent, 'looseVertices': loose_vertices,
              'looseEdges': loose_edges, 'degenerateGeometryTriangles': 0,
              'degenerateUvTriangles': 0, 'uvOutside01Loops': 0,
              'negativeVolumeComponents': 0, 'zeroVolumeComponents': 0,
              'invalidNormalTriangles': 0, 'unappliedModifiers': len(obj.modifiers),
              'uvUnexpectedOverlapPairs': 0, 'uvDeclaredFrontBackReusePairs': 0,
              'pairChecks': 0, 'auditComplete': True, 'examples': []}
    if uv_layer is None:
        result.update(passed=False, missingUv=True)
        return result
    result['uvOutside01Loops'] = sum(not (-1e-5 <= uv.uv.x <= 1.00001 and -1e-5 <= uv.uv.y <= 1.00001)
                                     for uv in uv_layer.data)
    volumes = defaultdict(list)
    triangles_by_component = defaultdict(list)
    for index, triangle in enumerate(mesh.loop_triangles):
        vertices = [mesh.vertices[v].co for v in triangle.vertices]
        component = component_ids[find(parents, triangle.vertices[0])]
        normal = (vertices[1]-vertices[0]).cross(vertices[2]-vertices[0])
        if normal.length*.5 <= GEOMETRY_AREA_EPS:
            result['degenerateGeometryTriangles'] += 1
            bounded_append(result['examples'], {'kind': 'degenerate_geometry', 'triangle': index,
                                               'polygon': triangle.polygon_index, 'component': component})
        if normal.length > 1e-15 and normal.normalized().dot(mesh.polygons[triangle.polygon_index].normal) <= 0:
            result['invalidNormalTriangles'] += 1
        volumes[component].append(vertices[0].dot(vertices[1].cross(vertices[2]))/6)
        uv = [tuple(uv_layer.data[loop].uv) for loop in triangle.loops]
        area = polygon_area(uv)
        if area <= UV_AREA_EPS:
            result['degenerateUvTriangles'] += 1
            bounded_append(result['examples'], {'kind': 'degenerate_uv', 'triangle': index,
                                               'polygon': triangle.polygon_index, 'component': component,
                                               'uvArea': area})
            continue
        triangles_by_component[component].append({'index': index, 'polygon': triangle.polygon_index,
            'uv': uv, 'area': area, 'normal': tuple(normal.normalized()),
            'bounds': (min(v[0] for v in uv), min(v[1] for v in uv),
                       max(v[0] for v in uv), max(v[1] for v in uv))})
    determinant_sign = -1 if obj.matrix_world.determinant() < 0 else 1
    for component, terms in volumes.items():
        volume = math.fsum(terms)*determinant_sign
        if volume < -1e-12:
            result['negativeVolumeComponents'] += 1
            bounded_append(result['examples'], {'kind': 'inward_component', 'component': component, 'signedVolume': volume})
        elif abs(volume) <= 1e-12:
            result['zeroVolumeComponents'] += 1
    # A 32x32 broadphase bounds candidate pairs. Exact clipping, not bounding-box
    # overlap, determines the result. Shared edges with zero area are accepted.
    for component, triangles in triangles_by_component.items():
        bins = defaultdict(list)
        for index, triangle in enumerate(triangles):
            u0, v0, u1, v1 = triangle['bounds']
            for x in range(max(0, min(31, int(math.floor(u0*32)))), max(0, min(31, int(math.floor(u1*32))))+1):
                for y in range(max(0, min(31, int(math.floor(v0*32)))), max(0, min(31, int(math.floor(v1*32))))+1):
                    bins[x, y].append(index)
        checked = set()
        for indices in bins.values():
            for ai in range(len(indices)):
                for bi in range(ai+1, len(indices)):
                    a, b = indices[ai], indices[bi]
                    pair = (min(a, b), max(a, b))
                    if pair in checked:
                        continue
                    checked.add(pair)
                    result['pairChecks'] += 1
                    if result['pairChecks'] > MAX_PAIR_CHECKS_PER_MESH:
                        result['auditComplete'] = False
                        result['boundedStopReason'] = 'pair_budget'
                        break
                    first, second = triangles[a], triangles[b]
                    ax0, ay0, ax1, ay1 = first['bounds']; bx0, by0, bx1, by1 = second['bounds']
                    if ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0:
                        continue
                    area = triangle_intersection_area(first['uv'], second['uv'])
                    if area <= max(OVERLAP_AREA_EPS, min(first['area'], second['area'])*1e-6):
                        continue
                    if allowed_sign_reuse(obj.name, first, second):
                        result['uvDeclaredFrontBackReusePairs'] += 1
                    else:
                        result['uvUnexpectedOverlapPairs'] += 1
                        bounded_append(result['examples'], {'kind': 'uv_overlap', 'component': component,
                            'triangles': [first['index'], second['index']],
                            'polygons': [first['polygon'], second['polygon']], 'area': area})
                if not result['auditComplete']:
                    break
            if not result['auditComplete']:
                break
        if not result['auditComplete']:
            break
    failures = ('nonManifoldEdges', 'inconsistentWindingEdges', 'looseVertices', 'looseEdges',
                'degenerateGeometryTriangles', 'degenerateUvTriangles', 'uvOutside01Loops',
                'negativeVolumeComponents', 'zeroVolumeComponents', 'invalidNormalTriangles',
                'unappliedModifiers', 'uvUnexpectedOverlapPairs')
    result['passed'] = result['auditComplete'] and all(result[key] == 0 for key in failures)
    return result


def main():
    if bpy.data.filepath.replace('\\', '/').lower() != EXPECTED_BLEND.lower():
        raise RuntimeError('Open the completed RB_P06_CanyonKit.blend source before this read-only audit.')
    meshes, missing = [], []
    for name in ASSETS:
        for lod in range(3):
            expected = 'RB_P06_' + name + '_L' + str(lod) + '_Mesh'
            obj = bpy.data.objects.get(expected)
            if obj is None or obj.type != 'MESH':
                missing.append(expected)
            else:
                meshes.append(audit_mesh(obj))
    result = {'passed': not missing and len(meshes) == 21 and all(m['passed'] for m in meshes),
        'scope': 'source mesh topology, orientation and exact UV triangle overlap within each connected component',
        'sourceBlend': bpy.data.filepath, 'blenderVersion': bpy.app.version_string,
        'meshCount': len(meshes), 'missing': missing, 'meshes': meshes,
        'crossComponentUvReuse': 'intentional repeated material surface reuse; not treated as an error',
        'explicitWithinComponentException': 'Chevron opposite front/back faces only; all side/bevel overlap remains an error',
        'limits': {'uvAreaEpsilon': UV_AREA_EPS, 'overlapAreaEpsilon': OVERLAP_AREA_EPS,
                   'maximumPairChecksPerMesh': MAX_PAIR_CHECKS_PER_MESH,
                   'maximumVerticesPerMesh': MAX_VERTICES_PER_MESH, 'maximumTrianglesPerMesh': MAX_TRIANGLES_PER_MESH},
        'limitations': ['No ray-tested geometric self-intersection audit.',
                        'UV float area thresholds are numerical, not a pixel-density quality guarantee.',
                        'No imported Unity mesh or gameplay-distance visual claim.',
                        'Source hash and timing bindings are recorded by the parent outside MCP.']}
    print(json.dumps(result))


main()
