import bpy,json
from mathutils import Vector
root=bpy.data.objects['RB_Golden_Apex_r3'];scene=bpy.context.scene;c=scene.camera;c.data.type='ORTHO';c.data.ortho_scale=2.5;c.location=(5,0,1.01);c.rotation_euler=(Vector((0,0,.60))-c.location).to_track_quat('-Z','Y').to_euler();scene.render.resolution_x=1400;scene.render.resolution_y=980;bpy.context.view_layer.update()
frame=c.data.view_frame(scene=scene);xmin=min(v.x for v in frame);xmax=max(v.x for v in frame);ymin=min(v.y for v in frame);ymax=max(v.y for v in frame);rows=[]
for x,y in [(774,545),(792,551),(790,563),(811,574),(788,535)]:
    origin=c.matrix_world@Vector((xmin+(xmax-xmin)*x/1400,ymin+(ymax-ymin)*(1-y/980),0));direction=c.matrix_world.to_quaternion()@Vector((0,0,-1))
    hit,p,n,idx,obj,matrix=scene.ray_cast(bpy.context.evaluated_depsgraph_get(),origin,direction)
    rows.append({'pixel':[x,y],'object':obj.name if hit else None,'normal':list(n),'polygon':idx,'material':obj.data.materials[obj.data.polygons[idx].material_index].name if hit else None})
for o in root.children_recursive:
    if not o.name.startswith('R3 Curved main fairing'):continue
    side=1 if o.name.endswith(' 1') else -1
    wrong=[p.index for p in o.data.polygons if p.normal.x*side>.8 and o.data.materials[p.material_index].name!='Apex_Pearl']
    rows.append({'object':o.name,'outerFaceBlack':wrong,'materialSlots':[m.name for m in o.data.materials]})
print('APEX_R3_CUT_MATERIAL '+json.dumps(rows))
