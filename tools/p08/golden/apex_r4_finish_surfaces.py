import bpy
import bmesh
import json
from mathutils import Vector

root = bpy.data.objects['RB_Golden_Apex_r4']
assert root.get('r4_compound_revision') == 1 and not root.get('r4_finish_revision')

def front_y(x, z):
    return .848 - .46 * (z - .850) - .25 * abs(x) - .8 * max(0, z - .966)

for side in [-1, 1]:
    obj = bpy.data.objects['R4 fitted windscreen side support ' + str(side)]
    for vertex in obj.data.vertices:
        index = vertex.index % (19 * 6)
        t, u = (index // 6) / 18, (index % 6) / 5
        a = Vector((side * (.145 - .009 * t), front_y(side * .145, .952) - .219 * t, .952 + .156 * t - .017 * t * t))
        old_b = Vector((side * (.228 - .037 * t), .730 - .220 * t, .924 + .097 * t))
        new_b = a + Vector((side * .032, .003, -.018))
        vertex.co += (new_b - old_b) * u
    obj.data.update()
    obj.data.normals_split_custom_set([(0, 0, 0)] * len(obj.data.loops))
    for prefix in ['R4 broad connected mirror arm ', 'R4 fairing mirror mount boot ']:
        obj = bpy.data.objects[prefix + str(side)]
        for vertex in obj.data.vertices:
            vertex.co.z += .039 * max(0, min(1, (vertex.co.y - .490) / .077))
        obj.data.update()

obj = bpy.data.objects['R4 compound stepped belly shell']
bm = bmesh.new()
bm.from_mesh(obj.data)
for face in bm.faces:
    face.smooth = True
for edge in bm.edges:
    direction = (edge.verts[1].co - edge.verts[0].co).normalized()
    edge.smooth = not (len(edge.link_faces) == 2 and abs(direction.y) > .55 and edge.calc_face_angle() > .35)
bm.to_mesh(obj.data)
bm.free()
obj.data.normals_split_custom_set([(0, 0, 0)] * len(obj.data.loops))
root['r4_finish_revision'] = 1
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
print('R4_FINISH=' + json.dumps({'screenSideSupportWidthMetres': .032, 'licensedGeometryImported': False, 'visualAccepted': False}))
