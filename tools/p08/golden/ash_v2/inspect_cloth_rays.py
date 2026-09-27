import bpy,json
from mathutils import Vector
obj=bpy.data.objects['AshV2_Clothes'];rows=[]
for z in [.473,.50,.54,.60,.67]:
    hits=[]
    for i in range(30):
        x=.05+i*.01;hit,p,n,index=obj.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))
        if hit:hits.append([round(x,3),round(p.y,4)])
    candidates=[v.co.x for v in obj.data.vertices if v.co.x>0 and abs(v.co.z-z)<.02]
    rows.append({'z':z,'hits':hits,'mesh_x_range':[min(candidates),max(candidates)] if candidates else []})
print(json.dumps({'ray_profile':rows,'modifiers':[m.name for m in obj.modifiers]}))
