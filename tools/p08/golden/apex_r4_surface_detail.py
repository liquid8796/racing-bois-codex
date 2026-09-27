"""Original compound side skins, connected mirror mounts and actual tyre grooves."""
import bpy,bmesh,math,json
from mathutils import Vector
scene=bpy.context.scene
root=bpy.data.objects['RB_Golden_Apex_r4']
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

assert not root.get('r4_compound_revision'), 'Apply compound remap only once'

def old_skin(z, y):
    points = [(.18, .142), (.36, .176), (.57, .212), (.72, .240), (.77, .242), (.83, .224), (.96, .161)]
    value = points[0][1]
    for (a, x), (b, height) in zip(points, points[1:]):
        if a <= z <= b:
            value = x + (height - x) * (z - a) / (b - a)
            break
        if z > b:
            value = height
    return value - .010 * math.exp(-((y - .08) / .13) ** 2 - ((z - .60) / .17) ** 2) - .040 * max(0, min(1, (y - .57) / .25))

def formed_skin(z, y):
    width = .155 + .123 * math.exp(-((z - .71) / .285) ** 2 - ((y - .40) / .36) ** 2)
    # Deep rear knee relief meets the exposed frame, while a convex shoulder
    # turns the main panel toward the cowl. A separate lower chine forms volume.
    width -= .055 * math.exp(-((z - .59) / .18) ** 2 - ((y - .095) / .19) ** 2)
    width -= .069 * max(0, min(1, (y - .54) / .25))
    width -= .031 * max(0, min(1, (.40 - z) / .20))
    return width

prefixes = ['R4 formed main fairing', 'R3 Recessed black intake return', 'R3 Intake plenum shadow',
            'R3 Recessed intake grille', 'R3 Fairing flush bolt', 'R3 Fairing bolt recess',
            'R3 Lower diagonal plenum', 'R3 Lower diagonal black cavity wall']
for obj in root.children_recursive:
    if obj.type != 'MESH' or not any(obj.name.startswith(p) for p in prefixes):
        continue
    matrix = obj.matrix_world.copy()
    inverse = matrix.inverted()
    for vertex in obj.data.vertices:
        point = matrix @ vertex.co
        side = 1 if point.x > 0 else -1
        point.x += side * (formed_skin(point.z, point.y) - old_skin(point.z, point.y))
        vertex.co = inverse @ point
    obj.data.update()
    obj.data.normals_split_custom_set([(0, 0, 0)] * len(obj.data.loops))

for obj in list(root.children_recursive):
    if obj.type == 'MESH' and (any(obj.name.startswith(p) for p in ['R3 Belly sculpted outer volume',
        'R3 Belly upper chine', 'R3 Closed sculpted sump', 'R4 short fairing mirror stem',
        'R4 flowing cowl shoulder return', 'Directional shallow tyre channel']) or obj.name in ['Front crowned road tyre', 'Rear crowned road tyre']):
        bpy.data.objects.remove(obj, do_unlink=True)

profile = [(0, 1), (.62, .99), (.92, .84), (1, .69), (.97, .47), (.84, .33), (.72, .13), (.45, 0),
           (0, 0), (-.45, 0), (-.72, .13), (-.84, .33), (-.97, .47), (-1, .69), (-.92, .84), (-.62, .99)]
sections = [(-.354, .235, .367, .133), (-.257, .216, .408, .178), (-.084, .199, .435, .205),
            (.160, .193, .452, .213), (.338, .194, .432, .189), (.474, .203, .289, .135)]
verts = []
faces = []
n = len(profile)
for k, (y, bottom, top, width) in enumerate(sections):
    verts.extend((x * width, y, bottom + z * (top - bottom)) for x, z in profile)
    if k:
        faces.extend(((k - 1) * n + j, (k - 1) * n + (j + 1) % n, k * n + (j + 1) % n, k * n + j) for j in range(n))
for k in [0, len(sections) - 1]:
    ci = len(verts)
    verts.append(sum((Vector(v) for v in verts[k * n:(k + 1) * n]), Vector()) / n)
    faces.extend((ci, k * n + j, k * n + (j + 1) % n) for j in range(n))
belly = surface('R4 compound stepped belly shell', verts, faces, 'Apex_Graphite', smooth=False)
bpy.context.view_layer.objects.active = belly
mod = belly.modifiers.new('Moulded belly edge radii', 'BEVEL')
mod.width = .002
mod.segments = 2
mod.limit_method = 'ANGLE'
mod.angle_limit = .20
bpy.ops.object.modifier_apply(modifier=mod.name)

def front_y(x, z):
    return .848 - .46 * (z - .850) - .25 * abs(x) - .8 * max(0, z - .966)

def screen_edge(side, t):
    return Vector((side * (.145 - .009 * t), front_y(side * .145, .952) - .219 * t, .952 + .156 * t - .017 * t * t))

for side in [-1, 1]:
    # Full cowl shoulder from optical housing back to the reshaped side panel.
    a = Vector((side * .234, front_y(.234, .966), .966))
    b = Vector((side * .232, front_y(.232, .885), .885))
    c = Vector((side * formed_skin(.84, .765), .765, .84))
    d = Vector((side * formed_skin(.920, .512), .512, .920))
    verts = []
    faces = []
    for r in range(9):
        t = r / 8
        for j in range(13):
            u = j / 12
            p = a * (1 - u) * (1 - t) + b * u * (1 - t) + c * u * t + d * (1 - u) * t
            p.x += side * .012 * math.sin(math.pi * u) * math.sin(math.pi * t)
            verts.append(p)
            if r and j:
                k = r * 13 + j
                faces.append((k - 14, k - 13, k, k - 1))
    surface('R4 integrated formed cowl shoulder ' + str(side), verts, faces, 'Apex_Pearl', .005, (side, .15, .3))
    # A substantial fairing side support follows the glass edge exactly.
    verts = []
    faces = []
    for r in range(19):
        t = r / 18
        a = screen_edge(side, t)
        b = Vector((side * (.228 - .037 * t), .730 - .220 * t, .924 + .097 * t))
        for j in range(6):
            u = j / 5
            verts.append(a * (1 - u) + b * u)
            if r and j:
                k = r * 6 + j
                faces.append((k - 7, k - 6, k, k - 1))
    surface('R4 fitted windscreen side support ' + str(side), verts, faces, 'Apex_Pearl', .005, (side, .2, .2))
    tube('R4 broad connected mirror arm ' + str(side), [(side * .180, .567, 1.016),
         (side * .222, .541, 1.034), (side * .272, .495, 1.051), (side * .307, .456, 1.061)], .0105, 'Apex_Graphite', 12)
    tube('R4 fairing mirror mount boot ' + str(side), [(side * .180, .566, 1.014), (side * .190, .558, 1.021)], .019, 'Apex_Graphite', 16)

# Genuine recessed directional tyre channels, replacing the previous raised
# decorative tubes. Fixed tread rings resolve each ~5mm-wide groove explicitly.
tyre_profile = [(-.50, .232), (-.51, .253), (-.49, .273), (-.44, .291), (-.35, .304),
                (-.25, .310), (-.14, .3135), (-.06, .3147), (0, .315), (.06, .3147),
                (.14, .3135), (.25, .310), (.35, .304), (.44, .291), (.49, .273), (.51, .253), (.50, .232)]
samples = [(0, 1), (.025, .88), (.052, 0), (.12, 0), (.30, 0), (.50, 0), (.70, 0), (.88, 0), (.948, 0), (.975, .88)]
for label, y_center, width in [('Front', .715, .130), ('Rear', -.715, .190)]:
    verts = []
    faces = []
    n = len(tyre_profile)
    ring_count = 32 * len(samples)
    for segment in range(32):
        for sample, depth in samples:
            base_angle = math.tau * (segment + sample) / 32
            i = segment * len(samples) + samples.index((sample, depth))
            for j, (x, radius) in enumerate(tyre_profile):
                angle = base_angle + .45 * abs(x) + (math.pi / 32 if x < 0 else 0)
                weight = min(1, max(0, (abs(x) - .018) / .065), max(0, (.47 - abs(x)) / .10))
                r = radius - .0035 * depth * weight
                verts.append((x * width, y_center + r * math.sin(angle), .315 + r * math.cos(angle)))
                ni, nj = (i + 1) % ring_count, (j + 1) % n
                faces.append((i * n + j, ni * n + j, ni * n + nj, i * n + nj))
    tyre = surface('R4 ' + label.lower() + ' tyre with recessed directional tread', verts, faces, 'Apex_Rubber')
    tyre['asset_group'] = label
    tyre['treadDepthMetres'] = .0035

# Rear-view concept has taller-than-wide rounded outlets, with rolled rims.
for obj in root.children_recursive:
    if obj.type != 'MESH' or not any(obj.name.startswith(p) for p in ['R4 under-seat titanium can',
        'R4 formed exhaust outlet rim', 'R4 dark recessed outlet liner', 'R4 exhaust deep dark recess', 'R4 can mounting band']):
        continue
    side = -1 if obj.name.split(' ')[-1] == '-1' or ' -1 ' in obj.name else 1
    for vertex in obj.data.vertices:
        p = vertex.co
        center_z = .916 - .347 * (p.y + .952)
        p.x = side * .047 + (p.x - side * .057) * .78
        p.z = center_z + (p.z - center_z) * 1.20
    obj.data.update()
root['r4_compound_revision'] = 1
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
print('R4_COMPOUND=' + json.dumps({'actualTreadDepthMetres': .0035, 'licensedMeshesImported': False,
      'separateMirrorMountsConnectedToCowl': True, 'visualAccepted': False}))

