import bpy
import json
from mathutils import Vector
s=bpy.data.scenes['Inspection_47f87e3d']
bpy.context.window.scene=s
bpy.context.view_layer.update()
rows=[]
for name in ['Object_18','Object_183','Object_185','Object_192','Object_196','Object_198','Object_206']:
 o=s.objects[name]
 pts=[o.matrix_world@v.co for v in o.data.vertices]
 lo=[min(v[i] for v in pts) for i in range(3)];hi=[max(v[i] for v in pts) for i in range(3)]
 rows.append({'name':name,'parent':o.parent.name if o.parent else None,'bounds':[lo,hi],'materials':[slot.material.name for slot in o.material_slots]})
print('PART_REPORT='+json.dumps(rows))
