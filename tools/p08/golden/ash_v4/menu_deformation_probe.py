import bpy,math,json
from mathutils import Vector,Matrix
rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene;old=rig.animation_data.action
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
base={b.name:b.matrix.copy() for b in rig.pose.bones};matrix=Matrix.Translation(Vector((0,0,-.017)))@Matrix.Rotation(math.radians(-65),4,'Z')
rig.animation_data.action=bpy.data.actions['RB_MenuHero'];scene.frame_set(1);bpy.context.view_layer.update()
rows=[]
for name in ['Hip','Torso','Head']:
    b=rig.pose.bones['RB_P06_Rider_L0_'+name];expected=matrix@base[b.name]
    rows.append({'bone':name,'translationDifference':(b.matrix.translation-expected.translation).length,'rotationDifferenceDegrees':math.degrees(b.matrix.to_quaternion().rotation_difference(expected.to_quaternion()).angle),'scale':list(b.matrix.to_scale())})
obj=bpy.data.objects['AshV4_L0_Skin'];evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=evaluated.to_mesh();displaced=[]
for v in obj.data.vertices:
    if .97<v.co.z<1.15 and abs(v.co.x)<.25:
        expected=matrix@v.co;actual=m.vertices[v.index].co
        if (actual-expected).length>.045:
            displaced.append({'vertex':v.index,'rest':list(v.co),'actual':list(actual),'difference':(actual-expected).length,'weights':[(obj.vertex_groups[g.group].name,g.weight) for g in v.groups]})
evaluated.to_mesh_clear();rig.animation_data.action=old;scene.frame_set(1)
print('ASH_V4_MENU_DEFORMATION '+json.dumps({'bones':rows,'waistLargeDeviationCount':len(displaced),'sample':displaced[:20]}))
