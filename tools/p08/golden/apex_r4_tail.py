"""Original R4 saddle/tail and exactly two under-seat outlet assemblies."""
import bpy,bmesh,math,json
from mathutils import Vector
scene=bpy.context.scene
root=bpy.data.objects['RB_Golden_Apex_r4']
def surface(name, vertices, faces, material, thickness=0, outward=None, smooth=True):
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

remove = ['R3 Sculpted enclosed tail', 'R3 Compact passenger saddle', 'R3 Fitted dark underseat tray',
          'R3 Full underseat moulded side enclosure', 'R3 Tail inset charcoal blade', 'Contoured rider saddle',
          'Saddle tailored perimeter', 'Under-seat titanium silencer', 'Hollow silencer end collar',
          'Dark inner exhaust wall', 'Recessed dark throat', 'Exhaust hanging strap',
          'Twin exhaust branch', 'Under-seat exhaust riser', 'Rear LED housing', 'Continuous rear LED',
          'Subframe upper rail']
for obj in list(root.children_recursive):
    if obj.type == 'MESH' and any(obj.name.startswith(prefix) for prefix in remove):
        bpy.data.objects.remove(obj, do_unlink=True)

def closed_loft(name, sections, profile, material, smooth=True):
    verts = []
    faces = []
    n = len(profile)
    for k, (y, bottom, top, width) in enumerate(sections):
        verts.extend((x * width, y, bottom + z * (top - bottom)) for x, z in profile)
        if k:
            for j in range(n):
                faces.append(((k - 1) * n + j, (k - 1) * n + (j + 1) % n, k * n + (j + 1) % n, k * n + j))
    for k in [0, len(sections) - 1]:
        ci = len(verts)
        verts.append(sum((Vector(v) for v in verts[k * n:(k + 1) * n]), Vector()) / n)
        faces.extend((ci, k * n + j, k * n + (j + 1) % n) for j in range(n))
    return surface(name, verts, faces, material, smooth=smooth)

shell = [(0, 1), (.60, .99), (.89, .91), (1, .74), (.985, .42), (.80, .10), (.53, 0),
         (0, 0), (-.53, 0), (-.80, .10), (-.985, .42), (-1, .74), (-.89, .91), (-.60, .99)]
closed_loft('R4 continuous faceted tail shell', [(-.948, .953, .991, .072), (-.873, .918, 1.009, .106),
            (-.773, .873, .991, .124), (-.665, .836, .944, .141), (-.568, .783, .867, .150),
            (-.475, .765, .816, .148), (-.337, .768, .799, .126), (-.220, .785, .817, .087)], shell, 'Apex_Pearl')
seat = [(0, 1), (.56, .98), (.84, .88), (.98, .64), (1, .30), (.86, .07), (.51, 0),
        (0, 0), (-.51, 0), (-.86, .07), (-1, .30), (-.98, .64), (-.84, .88), (-.56, .98)]
closed_loft('R4 fitted rider saddle', [(-.657, .870, .927, .108), (-.599, .832, .900, .132),
            (-.547, .808, .850, .143), (-.447, .794, .827, .141), (-.368, .794, .824, .131),
            (-.286, .797, .820, .110), (-.217, .804, .830, .064)], seat, 'Apex_Rubber')
closed_loft('R4 separate raised passenger pad', [(-.870, 1.004, 1.024, .072), (-.813, .993, 1.024, .098),
            (-.748, .969, 1.004, .107), (-.685, .936, .975, .103), (-.650, .925, .962, .094)], seat, 'Apex_Rubber')
for side in [-1, 1]:
    tube('R4 rider saddle edge seam ' + str(side), [(side * .105, -.646, .918), (side * .128, -.599, .888),
         (side * .137, -.547, .840), (side * .136, -.447, .818), (side * .126, -.368, .815),
         (side * .104, -.286, .812), (side * .060, -.220, .821)], .0015, 'Apex_Graphite', 8)
    tube('R4 exposed triangulated subframe ' + str(side), [(side * .095, -.772, .876),
         (side * .125, -.576, .778), (side * .141, -.251, .677)], .012, 'Apex_Graphite', 14)
    tube('R4 subframe diagonal strut ' + str(side), [(side * .110, -.672, .832),
         (side * .128, -.328, .784), (side * .141, -.251, .677)], .009, 'Apex_Graphite', 12)

def squircle(angle, radius_x, radius_z):
    c, s = math.cos(angle), math.sin(angle)
    return ((1 if c >= 0 else -1) * abs(c) ** .53 * radius_x,
            (1 if s >= 0 else -1) * abs(s) ** .53 * radius_z)

def exhaust_loop(name, center_x, rings, material):
    vertices = []
    faces = []
    n = 40
    for k, (y, z, rx, rz) in enumerate(rings):
        for j in range(n):
            x, height = squircle(math.tau * j / n, rx, rz)
            vertices.append((center_x + x, y, z + height))
        if k:
            faces.extend(((k - 1) * n + j, (k - 1) * n + (j + 1) % n,
                          k * n + (j + 1) % n, k * n + j) for j in range(n))
    # The profile wraps from outer shell to inner wall, making a closed solid
    # with a genuine recessed mouth, not an opaque end disc.
    faces.extend(((len(rings) - 1) * n + j, (len(rings) - 1) * n + (j + 1) % n,
                  (j + 1) % n, j) for j in range(n))
    return surface(name, vertices, faces, material)

for side in [-1, 1]:
    x = side * .057
    exhaust_loop('R4 under-seat titanium can ' + str(side), x,
        [(-.952, .916, .051, .037), (-.932, .910, .054, .040), (-.701, .830, .052, .040),
         (-.635, .808, .043, .034), (-.611, .800, .027, .025),
         (-.611, .800, .021, .019), (-.635, .808, .037, .028), (-.701, .830, .046, .034),
         (-.932, .910, .048, .034), (-.952, .916, .045, .031)], 'Apex_Titanium')
    exhaust_loop('R4 formed exhaust outlet rim ' + str(side), x,
        [(-.960, .919, .0515, .0375), (-.951, .916, .054, .040),
         (-.937, .911, .053, .039), (-.937, .911, .045, .031),
         (-.956, .918, .043, .029)], 'Apex_Machined')
    exhaust_loop('R4 dark recessed outlet liner ' + str(side), x,
        [(-.952, .916, .044, .030), (-.857, .883, .043, .029),
         (-.857, .883, .041, .027), (-.952, .916, .042, .028)], 'Apex_Graphite')
    tube('R4 exhaust deep dark recess ' + str(side), [(x, -.849, .880), (x, -.836, .876)], .030, 'Apex_Graphite', 24)
    tube('R4 exhaust inlet branch ' + str(side), [(0, -.452, .670),
         (x * .50, -.522, .726), (x * .88, -.576, .779), (x, -.618, .803)], .024, 'Apex_Titanium', 20)
    for index, (y, z) in enumerate([(-.751, .847), (-.870, .889)]):
        exhaust_loop('R4 can mounting band ' + str(side) + ' ' + str(index), x,
                     [(y - .006, z + .002, .055, .043), (y + .006, z - .002, .055, .043),
                      (y + .006, z - .002, .053, .041), (y - .006, z + .002, .053, .041)], 'Apex_Graphite')
        tube('R4 exhaust bracket ' + str(side) + ' ' + str(index), [(side * .106, y, z + .010),
             (side * .121, y + .025, z + .045)], .0055, 'Apex_Machined', 12)
tube('R4 swept exhaust collector riser', [(0, -.226, .333), (0, -.326, .394),
     (0, -.382, .487), (0, -.414, .586), (0, -.454, .673)], .031, 'Apex_Titanium', 24)
# Rear lamp sits above the two outlet openings, facing the rear along -Y.
surface('R4 rear lamp black carrier', [(-.074, -.959, .967), (.074, -.959, .967),
        (.071, -.962, .981), (-.071, -.962, .981)], [(0, 1, 2, 3)], 'Apex_Graphite', .008, (0, -1, 0))
surface('R4 continuous rear red strip', [(-.062, -.965, .971), (.062, -.965, .971),
        (.061, -.967, .977), (-.061, -.967, .977)], [(0, 1, 2, 3)], 'Apex_RedLamp', .002, (0, -1, 0))

bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
print('R4_TAIL=' + json.dumps({'underSeatOutlets': 2, 'riderSeatContactMetres': .824,
      'licensedMeshesImported': False, 'visualAccepted': False}))

