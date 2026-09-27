import bpy,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend',load_ui=False,use_scripts=False)
scene=bpy.context.scene;camera=scene.camera;camera.data.type='PERSP';camera.data.lens=68;camera.location=(-3.6,3.3,1.42);camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.resolution_x=1400;scene.render.resolution_y=980;bpy.context.view_layer.update()
frame=camera.data.view_frame(scene=scene);xmin=min(v.x for v in frame);xmax=max(v.x for v in frame);ymin=min(v.y for v in frame);ymax=max(v.y for v in frame);z=frame[0].z
rows=[]
for x,y in [(395,408),(408,425),(420,443),(435,459),(454,435),(389,435),(430,394)]:
    direction=camera.matrix_world.to_quaternion()@Vector((xmin+(xmax-xmin)*x/1400,ymin+(ymax-ymin)*(1-y/980),z)).normalized()
    hit,location,normal,index,obj,matrix=scene.ray_cast(bpy.context.evaluated_depsgraph_get(),camera.location,direction)
    rows.append({'pixel':[x,y],'object':obj.name if hit else None,'location':list(location),'material':obj.data.materials[obj.data.polygons[index].material_index].name if hit and obj.type=='MESH' else None})
print('APEX_R3_VISUAL_RAYS '+json.dumps(rows))
