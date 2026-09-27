import bpy,json
from mathutils import Vector
rig=bpy.data.objects['RB_P06_Rider_Rig'];obj=bpy.data.objects['AshV2_L0_Skin'];depsgraph=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(depsgraph)
hits=[]
for x in [.03,.048,.07]:
    hit,p,n,index=evaluated.ray_cast(Vector((x,-1,1.756)),Vector((0,1,0)))
    hits.append({'x':x,'hit':hit,'point':list(p),'material':evaluated.data.materials[evaluated.data.polygons[index].material_index].name if hit else None})
print(json.dumps({'savedSource':bpy.data.filepath,'dirty':bpy.data.is_dirty,'action':rig.animation_data.action.name if rig.animation_data.action else None,'frame':bpy.context.scene.frame_current,'temporaryHeadAbsent':bpy.data.objects.get('AshV2_TemporaryHeadInspection') is None,'lensRays':hits}))
