import bpy,json
from mathutils import Vector
assert bpy.data.filepath.replace('\\','/').endswith('/Spark/V2/RB_Golden_Spark_v2_refined05.blend')
rows=[]
for y in [-.10,-.05,0,.05,.10,.15,.20,.25,.30,.35,.375,.40,.425]:
    shapes=[]
    for name in ['Upper black frame rail 1','Steering head','Upper triple clamp']:
        obj=bpy.data.objects[name];points=[]
        for edge in obj.data.edges:
            a,b=[obj.matrix_world@obj.data.vertices[i].co for i in edge.vertices]
            if abs(b.y-a.y)<1e-9:continue
            t=(y-a.y)/(b.y-a.y)
            if 0<=t<=1:points.append(a+(b-a)*t)
        if points:shapes.append({'name':name,'minX':min(p.x for p in points),'maxX':max(p.x for p in points),'minZ':min(p.z for p in points),'maxZ':max(p.z for p in points)})
    rows.append({'y':y,'sections':shapes})
print('SPARK_TANK_PROFILE_PROBE='+json.dumps(rows))
