import bpy,json,math,array
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];root=bpy.data.objects['RB_Golden_Ash_V7'];scene=bpy.context.scene
lods=[bpy.data.objects['AshV7_L'+str(i)+'_Skin'] for i in range(3)]
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for obj in lods:
    for key in obj.data.shape_keys.key_blocks:key.value=0
bpy.context.view_layer.update();static=[]
for obj in lods:
    mesh=obj.data;mesh.calc_loop_triangles();bad=0;uv_bad=0;min_cross=1
    for tri in mesh.loop_triangles:
        a,b,c=[mesh.vertices[i].co for i in tri.vertices];cross=(b-a).cross(c-a).length_squared;min_cross=min(min_cross,cross);bad+=cross<=1e-16
        a,b,c=[mesh.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a;uv_bad+=abs(ab.x*ac.y-ab.y*ac.x)<=1e-14
    assert bad==0 and uv_bad==0,'Geometry/UV gate failed'
    for v in mesh.vertices:
        weights=[g.weight for g in v.groups if g.weight>.00001]
        assert 0<len(weights)<=4 and abs(sum(weights)-1)<.0002
    static.append({'name':obj.name,'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),'physicalFailures':bad,'primaryUvFailures':uv_bad,'minimumCrossSquared':min_cross})
clips=[]
for action in bpy.data.actions:
    if not action.name.startswith('RB_'):continue
    rig.animation_data.action=action;start,end=action.frame_range;bounds=[]
    for amount in [0,.25,.5,.75,1]:
        frame=start+(end-start)*amount;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
        assert all(math.isfinite(v) for b in rig.pose.bones for row in b.matrix for v in row)
        points=[]
        for obj in lods:
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh();data=array.array('f',[0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',data)
            assert all(math.isfinite(v) for v in data),'Nonfinite deformed mesh'
            minimum=[min(data[a::3]) for a in range(3)];maximum=[max(data[a::3]) for a in range(3)];points.extend([minimum,maximum]);evaluated.to_mesh_clear()
        bounds.append({'normalizedTime':amount,'min':[min(p[a] for p in points) for a in range(3)],'max':[max(p[a] for p in points) for a in range(3)]})
    clips.append({'name':action.name,'frames':[start,end],'deformationSamples':bounds})
assert len(clips)==13 and len(rig.data.bones)==45
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
selection=[root,rig]+lods+[bpy.data.objects[n] for n in ['Forward','Ground_L','Ground_R']]
for obj in selection:obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=root
path=ROOT+'_local/p08-ash-v7-staging/RB_Golden_Ash_V7.fbx'
bpy.ops.export_scene.fbx(filepath=path,use_selection=True,object_types={'MESH','ARMATURE','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
    use_mesh_modifiers=False,add_leaf_bones=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=True,
    bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='STRIP')
for i,obj in enumerate(lods):obj.hide_set(i!=0);obj.hide_render=i!=0
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_AUDIT_EXPORT '+json.dumps({'passed':True,'fbx':path,'bones':45,'lods':static,'clips':clips,'sourceOnlyExport':True,'visualAcceptance':False,'nativeAcceptance':False}))
