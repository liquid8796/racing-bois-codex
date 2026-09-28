"""Read-only actual07 view hits to identify rear ridge corrections."""
import bpy,json
from mathutils import Vector
if not bpy.data.filepath.replace('\\','/').endswith('/Canyon/V19/RB_Golden_Canyon_V19_07.blend'):raise RuntimeError('Expected07.')
scene=bpy.context.scene;camera=scene.camera;frame=camera.data.view_frame(scene=scene)
x0,x1=min(p.x for p in frame),max(p.x for p in frame);y0,y1=min(p.y for p in frame),max(p.y for p in frame)
graph=bpy.context.evaluated_depsgraph_get();hits=[]
for px in [450,500,550,600,650,700,750,800,850,900,1000,1100]:
    for py in [60,100,140,180,220,260,290]:
        direction=(camera.matrix_world.to_quaternion()@Vector((x0+(x1-x0)*px/1536,y1-(y1-y0)*py/717,frame[0].z))).normalized()
        origin=camera.matrix_world.translation.copy();value=None
        for step in range(20):
            hit,point,normal,face,obj,matrix=scene.ray_cast(graph,origin,direction,distance=2500)
            if not hit:break
            if obj.name.startswith('Canyon_L0_'):
                value={'object':obj.name,'world':list(point)};break
            origin=point+direction*.01
        hits.append({'pixel':[px,py],'hit':value})
print('CANYON_V19_SKYLINE07 '+json.dumps({'hits':hits,'cameraMatrix':[list(r) for r in camera.matrix_world],
    'viewFrame':[list(p) for p in frame],'sourceSaved':False}))
