"""Original swept optical cowl, fitted screen and mirror cases for R4."""
import bpy
import bmesh
import math
import json
from mathutils import Vector

scene = bpy.context.scene
root = bpy.data.objects['RB_Golden_Apex_r4']
prefixes = ['R3 Unified curved front cowl', 'R3 Moulded optical black lip', 'R3 Closed dark headlight backing',
            'R3 Optical cavity depth', 'R3 Compound curved protective lens', 'R3 Single projector bezel',
            'R3 Single main projector', 'R3 Projector lens lip', 'R3 Cowl side return', 'R3 Mirror stalk',
            'R3 Rounded trapezoid mirror case', 'R3 Recessed rear mirror glass', 'R3 Continuous graphite centre spine',
            'R3 Swept attached smoked screen', 'R3 Screen fitted rim', 'R3 Screen base seated gasket']
prefixes += ['R4 swept continuous optical cowl', 'R4 recessed optical seal', 'R4 headlamp aperture depth',
             'R4 closed black lamp back', 'R4 flush swept clear lens', 'R4 machined projector ring',
             'R4 luminous recessed projector', 'R4 flowing cowl shoulder return', 'R4 fitted central nose blade',
             'R4 attached double-curved windscreen', 'R4 screen lower seated seal', 'R4 screen thin side rim',
             'R4 short fairing mirror stem', 'R4 angular mirror housing', 'R4 rear-facing mirror glass',
             'R4 fitted screen collar', 'R4 continuous lower nose return']
for obj in list(root.children_recursive):
    if any(obj.name.startswith(prefix) for prefix in prefixes):
        bpy.data.objects.remove(obj, do_unlink=True)

def surface(name, vertices, faces, material, thickness=0, outward=None, smooth=True):
    vertices = list(vertices)
    triangulated = []
    for face in faces:
        if len(face) <= 4:
            triangulated.append(face)
            continue
        center = sum((Vector(vertices[i]) for i in face), Vector()) / len(face)
        index = len(vertices)
        vertices.append(center)
        for j in range(len(face)):
            triangulated.append((index, face[j], face[(j + 1) % len(face)]))
    mesh = bpy.data.meshes.new(name + ' mesh')
    mesh.from_pydata(vertices, [], triangulated)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.parent = root
    obj['asset_group'] = 'Body'
    mesh.materials.append(bpy.data.materials[material])
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if outward is not None:
        normal = sum((f.normal * f.calc_area() for f in bm.faces), Vector())
        if normal.dot(Vector(outward)) < 0:
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    for face in mesh.polygons:
        face.use_smooth = smooth
    bpy.context.view_layer.objects.active = obj
    if thickness:
        if material == 'Apex_Pearl':
            mesh.materials.append(bpy.data.materials['Apex_Graphite'])
        mod = obj.modifiers.new('Moulded wall thickness', 'SOLIDIFY')
        mod.thickness = thickness
        mod.offset = -1
        if material == 'Apex_Pearl':
            mod.material_offset = 1
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

def filleted_loop(points, fraction=.1, steps=4):
    result = []
    for i, raw in enumerate(points):
        p = Vector(raw)
        a = p + (Vector(points[(i - 1) % len(points)]) - p) * fraction
        b = p + (Vector(points[(i + 1) % len(points)]) - p) * fraction
        for j in range(steps + 1):
            t = j / steps
            result.append(a * (1 - t) ** 2 + p * 2 * t * (1 - t) + b * t * t)
        following = Vector(points[(i + 1) % len(points)])
        end = following + (p - following) * fraction
        for j in range(1, 4):
            result.append(b * (1 - j / 4) + end * j / 4)
    return result

def tube(name, centers, radius, material, sides=16):
    centers = [Vector(p) for p in centers]
    verts = []
    faces = []
    for k, point in enumerate(centers):
        axis = (centers[min(k + 1, len(centers) - 1)] - centers[max(0, k - 1)]).normalized()
        helper = Vector((0, 0, 1)) if abs(axis.z) < .9 else Vector((1, 0, 0))
        u = axis.cross(helper).normalized()
        v = axis.cross(u).normalized()
        for j in range(sides):
            angle = math.tau * j / sides
            verts.append(point + radius * (u * math.cos(angle) + v * math.sin(angle)))
            if k:
                faces.append(((k - 1) * sides + j, (k - 1) * sides + (j + 1) % sides,
                              k * sides + (j + 1) % sides, k * sides + j))
    for k, reverse in [(0, True), (len(centers) - 1, False)]:
        ci = len(verts)
        verts.append(centers[k])
        for j in range(sides):
            face = (ci, k * sides + j, k * sides + (j + 1) % sides)
            faces.append(tuple(reversed(face)) if reverse else face)
    return surface(name, verts, faces, material)

def front_y(x, height):
    return .848 - .46 * (height - .850) - .25 * abs(x) - .8 * max(0, height - .966)

def on_cowl(x, height):
    return Vector((x, front_y(x, height), height))

outer_xz = [(.007, .802), (.009, .928), (.147, .997), (.234, .966), (.232, .885), (.170, .848)]
inner_xz = [(.030, .828), (.041, .900), (.190, .940), (.215, .925), (.209, .889), (.154, .851)]
for side in [-1, 1]:
    outer = filleted_loop(outer_xz, .10)
    aperture = filleted_loop(inner_xz, .08)
    count = len(outer)
    vertices = []
    faces = []
    for k in range(7):
        t = k / 6
        for j in range(count):
            x, height = outer[j] * (1 - t) + aperture[j] * t
            p = on_cowl(side * x, height)
            p.y += .006 * math.sin(math.pi * t)
            vertices.append(p)
            if k:
                faces.append(((k - 1) * count + j, (k - 1) * count + (j + 1) % count,
                              k * count + (j + 1) % count, k * count + j))
    surface('R4 swept continuous optical cowl ' + str(side), vertices, faces, 'Apex_Pearl', .005, (side * .2, 1, .3))
    edge = [on_cowl(side * x, height) for x, height in aperture]
    center = sum(edge, Vector()) / count
    lip = [center + (p - center) * .952 for p in edge]
    ring = [(j, (j + 1) % count, count + (j + 1) % count, count + j) for j in range(count)]
    surface('R4 recessed optical seal ' + str(side), edge + lip, ring, 'Apex_Graphite', .004, (0, 1, 0))
    rear = [p - Vector((0, .060, 0)) for p in lip]
    surface('R4 headlamp aperture depth ' + str(side), lip + rear, ring, 'Apex_Graphite', .003)
    surface('R4 closed black lamp back ' + str(side), rear, [tuple(range(count))], 'Apex_Graphite', .004, (0, 1, 0), False)
    # Optical cover follows the aperture, with a subtle compound curvature.
    verts = []
    faces = []
    for k, fraction in enumerate([1, .78, .54, .27]):
        for p in lip:
            verts.append(center + (p - center) * fraction + Vector((0, .001 + .004 * (1 - fraction ** 2), 0)))
        if k:
            for j in range(count):
                faces.append(((k - 1) * count + j, (k - 1) * count + (j + 1) % count,
                              k * count + (j + 1) % count, k * count + j))
    ci = len(verts)
    verts.append(center + Vector((0, .005, 0)))
    for j in range(count):
        faces.append((3 * count + j, 3 * count + (j + 1) % count, ci))
    surface('R4 flush swept clear lens ' + str(side), verts, faces, 'Apex_Lens', .0015, (0, 1, 0))
    lamp = on_cowl(side * .138, .887) - Vector((0, .029, 0))
    # A lathed closed projector ring with a recessed luminous lens.
    verts = []
    faces = []
    profile = [(-.016, .018), (-.019, .030), (-.011, .035), (.006, .034), (.010, .030), (.007, .025), (-.013, .024)]
    for depth, radius in profile:
        for j in range(48):
            a = math.tau * j / 48
            verts.append(lamp + Vector((math.cos(a) * radius, depth, math.sin(a) * radius)))
    for k in range(len(profile)):
        next_k = (k + 1) % len(profile)
        for j in range(48):
            faces.append((k * 48 + j, k * 48 + (j + 1) % 48, next_k * 48 + (j + 1) % 48, next_k * 48 + j))
    surface('R4 machined projector ring ' + str(side), verts, faces, 'Apex_Machined')
    tube('R4 luminous recessed projector ' + str(side), [lamp - Vector((0, .015, 0)), lamp - Vector((0, .010, 0))], .023, 'Apex_Lamp', 48)
    # The cheek rolls back into the side fairing, enclosing the visible gap.
    a = on_cowl(side * .234, .966)
    b = on_cowl(side * .232, .885)
    c = Vector((side * .183, .765, .840))
    d = Vector((side * .180, .512, .920))
    verts = []
    faces = []
    for row in range(9):
        t = row / 8
        for col in range(13):
            u = col / 12
            p = a * (1 - u) * (1 - t) + b * u * (1 - t) + c * u * t + d * (1 - u) * t
            p.x += side * .008 * math.sin(math.pi * u) * math.sin(math.pi * t)
            verts.append(p)
            if row and col:
                k = row * 13 + col
                faces.append((k - 14, k - 13, k, k - 1))
    surface('R4 flowing cowl shoulder return ' + str(side), verts, faces, 'Apex_Pearl', .006, (side, .2, .2))

# Central cowl fills the space between the two explicitly matched outer edges.
vertices = []
faces = []
for row in range(19):
    t = row / 18
    height = .796 + (.992 - .796) * t
    width = .007 + .002 * min(1, (height - .796) / .132)
    if height > .928:
        width = .009 + (.147 - .009) * (height - .928) / (.069)
    for j in range(13):
        x = (j / 6 - 1) * width
        vertices.append(on_cowl(x, height) + Vector((0, .001, 0)))
        if row and j:
            k = row * 13 + j
            faces.append((k - 14, k - 13, k, k - 1))
surface('R4 fitted central nose blade', vertices, faces, 'Apex_Graphite', .004, (0, 1, .2))

vertices = []
faces = []
for row in range(3):
    for col in range(49):
        x = (col / 24 - 1) * .226
        a = abs(x)
        height = .802 + max(0, a - .007) * (.046 / .163) if a <= .170 else .848 + (a - .170) * (.037 / .062)
        height -= row * .007
        vertices.append(on_cowl(x, height))
        if row and col:
            k = row * 49 + col
            faces.append((k - 50, k - 49, k, k - 1))
surface('R4 continuous lower nose return', vertices, faces, 'Apex_Pearl', .004, (0, 1, -.2))

def screen_point(q, t):
    height = .992 - .040 * q * q
    x = q * (.145 - .009 * t)
    forward = front_y(q * .145, height) - .207 * t - .012 * q * q * t
    forward += .018 * (1 - q * q) * math.sin(math.pi * t)
    return Vector((x, forward, height + .150 * t - .017 * t * t + .006 * q * q * t))

vertices = []
faces = []
for row in range(19):
    for col in range(29):
        vertices.append(screen_point(col / 14 - 1, row / 18))
        if row and col:
            k = row * 29 + col
            faces.append((k - 30, k - 29, k, k - 1))
surface('R4 attached double-curved windscreen', vertices, faces, 'Apex_Glass', .003, (0, 1, .7))
tube('R4 screen lower seated seal', [screen_point(i / 16 - 1, 0) for i in range(33)], .003, 'Apex_Graphite', 10)
vertices = []
faces = []
for row in range(5):
    t = row / 4
    for col in range(29):
        q = col / 14 - 1
        base = screen_point(q, 0)
        low = on_cowl(q * .165, base.z - .043)
        vertices.append(base * (1 - t) + low * t)
        if row and col:
            k = row * 29 + col
            faces.append((k - 30, k - 29, k, k - 1))
surface('R4 fitted screen collar', vertices, faces, 'Apex_Pearl', .004, (0, 1, .3))
for side in [-1, 1]:
    tube('R4 screen thin side rim ' + str(side), [screen_point(side, i / 18) for i in range(19)], .002, 'Apex_Graphite', 8)
    tube('R4 short fairing mirror stem ' + str(side), [(side * .203, .586, .987), (side * .259, .530, 1.031), (side * .303, .486, 1.057)], .0065, 'Apex_Graphite')
    loop = filleted_loop([(side * .279, .474, 1.032), (side * .369, .464, 1.045),
                          (side * .378, .430, 1.089), (side * .305, .416, 1.098)], .12)
    center = sum(loop, Vector()) / len(loop)
    n = len(loop)
    verts = []
    faces = []
    for k, (factor, depth) in enumerate([(.88, .020), (1, .008), (1, -.018), (.90, -.023)]):
        verts.extend(center + (p - center) * factor + Vector((0, depth, 0)) for p in loop)
        if k:
            faces.extend(((k - 1) * n + j, (k - 1) * n + (j + 1) % n, k * n + (j + 1) % n, k * n + j) for j in range(n))
    for k in [0, 3]:
        ci = len(verts)
        verts.append(sum(verts[k * n:(k + 1) * n], Vector()) / n)
        for j in range(n):
            faces.append((ci, k * n + j, k * n + (j + 1) % n))
    surface('R4 angular mirror housing ' + str(side), verts, faces, 'Apex_Graphite')
    surface('R4 rear-facing mirror glass ' + str(side), [center + (p - center) * .84 + Vector((0, -.024, 0)) for p in loop],
            [tuple(range(n))], 'Apex_Machined', .0015, (0, -1, 0), False)

# Smooth broad tank sections; preserve the long shoulder/knee crease edges.
tank = bpy.data.objects['R4 angular pressed fuel tank']
bm = bmesh.new()
bm.from_mesh(tank.data)
for face in bm.faces:
    face.smooth = True
for edge in bm.edges:
    direction = (edge.verts[1].co - edge.verts[0].co).normalized()
    edge.smooth = not (len(edge.link_faces) == 2 and abs(direction.y) > .72 and edge.calc_face_angle() > .28)
bm.to_mesh(tank.data)
bm.free()
tank.data.normals_split_custom_set([(0, 0, 0)] * len(tank.data.loops))
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
print('R4_COWL=' + json.dumps({'licensedMeshesImported': False, 'visualAccepted': False, 'projectors': 2, 'screenAttached': True}))
