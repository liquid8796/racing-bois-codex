import bpy
import json
from mathutils import Vector
obj = bpy.data.objects['R4 continuous faceted tail shell']
assert not obj.get('saddle_clearance_revision'), 'Do not apply the clearance displacement twice'
for vertex in obj.data.vertices:
    y = vertex.co.y
    amount = 0
    if -.725 < y < -.210:
        if y < -.62:
            amount = .027 * (y + .725) / .105
        elif y < -.52:
            amount = .027
        else:
            amount = .004 + .023 * (-.210 - y) / .31
        vertex.co.z -= amount
obj['saddle_clearance_revision'] = 1
obj.data.update()
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
rows = []
bpy.context.view_layer.update()
for y in [-.65, -.55, -.447, -.37, -.29]:
    hit, point, normal, index, obj, matrix = bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((0, y, 2)), Vector((0, 0, -1)))
    rows.append({'y': y, 'z': point.z, 'object': obj.name})
print('R4_SEAT_CLEARANCE=' + json.dumps(rows))
