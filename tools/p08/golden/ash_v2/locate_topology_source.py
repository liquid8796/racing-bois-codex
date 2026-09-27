import bpy,json
from mathutils import Vector
collection=bpy.data.collections['AshV2_Editable_Source'];collection.hide_viewport=False;bpy.context.view_layer.update();depsgraph=bpy.context.evaluated_depsgraph_get()
probe=Vector((.223987475,-.038631164,.270715266));rows=[]
for obj in collection.objects:
    if obj.type!='MESH' or obj.name=='AshV2_HighResSource':continue
    if not any(m and m.name=='AshV2_BootLeather' for m in obj.data.materials):continue
    mesh=obj.evaluated_get(depsgraph).to_mesh();distance=min((v.co-probe).length for v in mesh.vertices)
    rows.append({'name':obj.name,'distance':distance});obj.evaluated_get(depsgraph).to_mesh_clear()
collection.hide_viewport=True
def score(row):return row['distance']
rows.sort(key=score);print(json.dumps(rows[:5]))
