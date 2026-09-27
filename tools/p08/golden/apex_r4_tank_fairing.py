"""Original R4 tank/control surfaces. Reference GLBs are never loaded here."""
import bpy
import bmesh
import math
import json
from mathutils import Vector

scene = bpy.context.scene
root = bpy.data.objects['RB_Golden_Apex_r4']
assert 'R4 angular pressed fuel tank' not in bpy.data.objects, 'Run once on prepared R3 copy'

def finish_mesh(name, vertices, faces, material, bevel=0):
    mesh = bpy.data.meshes.new(name + ' mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.parent = root
    obj['asset_group'] = 'Body'
    mesh.materials.append(bpy.data.materials[material])
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    for face in mesh.polygons:
        face.use_smooth = False
    bpy.context.view_layer.objects.active = obj
    if bevel:
        mod = obj.modifiers.new('Pressed edge fillets', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = 'ANGLE'
        mod.angle_limit = .18
        mod.harden_normals = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh = obj.data
    uv = mesh.uv_layers.new(name='UV0_SurfaceMetres')
    for face in mesh.polygons:
        axis = 0 if abs(face.normal.x) >= max(abs(face.normal.y), abs(face.normal.z)) else 1 if abs(face.normal.y) >= abs(face.normal.z) else 2
        axes = [i for i in range(3) if i != axis]
        for loop in face.loop_indices:
            p = mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv = (p[axes[0]] * 2, p[axes[1]] * 2)
    return obj

def ring_volume(name, sections, half_profile, material, bevel):
    profile = half_profile + [(-x, z) for x, z in reversed(half_profile[1:-1])]
    count = len(profile)
    vertices = []
    faces = []
    for k, (forward, bottom, top, width) in enumerate(sections):
        vertices.extend((x * width, forward, bottom + z * (top - bottom)) for x, z in profile)
        if k:
            for j in range(count):
                faces.append(((k - 1) * count + j, (k - 1) * count + (j + 1) % count,
                              k * count + (j + 1) % count, k * count + j))
    # Profiles are concave at the knee. Use a cross-section fill constrained by
    # its actual boundary rather than a fan through a concavity.
    mesh = finish_mesh(name, vertices, faces, material)
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    boundary = [edge for edge in bm.edges if edge.is_boundary]
    bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh.data)
    bm.free()
    bpy.context.view_layer.objects.active = mesh
    mod = mesh.modifiers.new('Tank pressed crease radius', 'BEVEL')
    mod.width = bevel
    mod.segments = 3
    mod.limit_method = 'ANGLE'
    mod.angle_limit = .22
    mod.harden_normals = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Rebuild the finish UV after fillets and cap triangulation.
    data = mesh.data
    uv = data.uv_layers.active
    for face in data.polygons:
        axis = 0 if abs(face.normal.x) >= max(abs(face.normal.y), abs(face.normal.z)) else 1 if abs(face.normal.y) >= abs(face.normal.z) else 2
        axes = [i for i in range(3) if i != axis]
        for loop in face.loop_indices:
            p = data.vertices[data.loops[loop].vertex_index].co
            uv.data[loop].uv = (p[axes[0]] * 2, p[axes[1]] * 2)
    return mesh

for name in ['R3 Pressed tank with held shoulder and knee scallops', 'R3 Tank underside closed mounting']:
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)

# The side scallop is a real concavity beneath the held shoulder. Longitudinal
# planes are authored deliberately; no generic rounded capsule or inflated loft.
half = [(0, 1), (.38, .995), (.64, .94), (.71, .885), (.95, .72), (1, .66),
        (.995, .55), (.88, .40), (.62, .29), (.53, .15), (.70, .055), (.70, 0), (0, 0)]
sections = [(-.230, .786, .829, .078), (-.185, .773, .883, .101),
            (-.114, .768, .977, .156), (-.045, .778, 1.024, .185),
            (.080, .793, 1.035, .204), (.193, .805, 1.016, .200),
            (.294, .818, .973, .176), (.376, .835, .920, .114), (.397, .840, .899, .076)]
tank = ring_volume('R4 angular pressed fuel tank', sections, half, 'Apex_Pearl', .0032)
ring_volume('R4 tank mounting underside', [(-.229, .773, .799, .075), (-.10, .753, .792, .092),
            (.10, .770, .814, .108), (.30, .810, .840, .13), (.394, .826, .850, .07)],
            [(0, 1), (.8, 1), (1, .5), (.8, 0), (0, 0)], 'Apex_Graphite', .0015)

def old_surface(height, forward):
    waist = .014 * math.exp(-((height - .59) / .14) ** 2 - ((forward - .10) / .19) ** 2)
    shoulder = .020 * math.exp(-((height - .79) / .18) ** 2 - ((forward - .38) / .27) ** 2)
    return .224 + shoulder - waist - .091 * ((height - .76) / .60) ** 2 - .018 * max(0, forward - .62) / .20

def new_surface(height, forward):
    points = [(.18, .142), (.36, .176), (.57, .212), (.72, .240), (.77, .242), (.83, .224), (.96, .161)]
    value = points[0][1]
    for (a, x), (b, y) in zip(points, points[1:]):
        if a <= height <= b:
            value = x + (y - x) * (height - a) / (b - a)
            break
        if height > b:
            value = y
    rear_scallop = .010 * math.exp(-((forward - .08) / .13) ** 2 - ((height - .60) / .17) ** 2)
    front_wrap = .040 * max(0, min(1, (forward - .57) / .25))
    return value - rear_scallop - front_wrap

remapped = []
prefixes = ['R3 Curved main fairing', 'R3 Recessed black intake return', 'R3 Intake plenum shadow',
            'R3 Recessed intake grille', 'R3 Fairing flush bolt', 'R3 Fairing bolt recess',
            'R3 Lower diagonal plenum', 'R3 Lower diagonal black cavity wall']
for obj in root.children_recursive:
    if obj.type != 'MESH' or not any(obj.name.startswith(prefix) for prefix in prefixes):
        continue
    world = obj.matrix_world.copy()
    inverse = world.inverted()
    for vertex in obj.data.vertices:
        p = world @ vertex.co
        side = 1 if p.x > 0 else -1
        p.x += side * (new_surface(p.z, p.y) - old_surface(p.z, p.y))
        vertex.co = inverse @ p
    obj.data.update()
    if obj.name.startswith('R3 Curved main fairing'):
        obj.name = obj.name.replace('R3 Curved main fairing', 'R4 formed main fairing')
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new('Manufactured perimeter radius', 'BEVEL')
        mod.width = .0012
        mod.segments = 2
        mod.limit_method = 'ANGLE'
        mod.angle_limit = .55
        mod.harden_normals = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    remapped.append(obj.name)

scene.cycles.device = 'CPU'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.cycles.samples = 20
scene.render.resolution_x = 1280
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
print('R4_TANK_FAIRING=' + json.dumps({'tankVertices': len(tank.data.vertices), 'remappedMeshes': len(remapped),
      'licensedMeshesImported': False, 'visualAccepted': False, 'stage': 'Tank and fairing first render; nose/tail remain R3 pending correction'}))
