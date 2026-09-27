import bpy,json
from mathutils import Vector
rows=[]
for x in [0,.05,.10]:
 for y in [-.65,-.55,-.447,-.37,-.29]:
  hit,p,n,index,obj,matrix=bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(),Vector((x,y,2)),Vector((0,0,-1)))
  rows.append({'x':x,'y':y,'hit':hit,'z':p.z if hit else None,'object':obj.name if obj else None,'material':obj.data.materials[obj.data.polygons[index].material_index].name if hit else None})
print(json.dumps(rows))
