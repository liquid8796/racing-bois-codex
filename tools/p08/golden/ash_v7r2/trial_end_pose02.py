import bpy,json,math
from mathutils import Vector,Quaternion,Matrix
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend',load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_Fall'];scene.frame_set(19);bpy.context.view_layer.update();rig.animation_data.action=None
hip=rig.pose.bones['RB_P06_Rider_L0_Hip'];rest=hip.bone.matrix_local.to_quaternion();body=Quaternion((0,1,0),math.radians(90))
hip.rotation_quaternion=rest.inverted()@body@rest;bpy.context.view_layer.update()
def aim(part,direction):
    p=rig.pose.bones['RB_P06_Rider_L0_'+part];old_location=p.location.copy();old_scale=p.scale.copy();current=p.matrix.copy()
    delta=(p.tail-p.head).normalized().rotation_difference((body@Vector(direction)).normalized());rotation=delta@current.to_quaternion()
    p.matrix=Matrix.Translation(p.head)@rotation.to_matrix().to_4x4();p.location=old_location;p.scale=old_scale;bpy.context.view_layer.update()
aim('Torso',(-.10,-.18,.978));aim('Head',(.50,-.04,.865))
aim('UpperArm_L',(-.18,-.65,-.58));aim('Forearm_L',(-.40,-.12,.90));aim('Hand_L',(-.25,-.10,.96))
aim('UpperArm_R',(.25,-.65,-.72));aim('Forearm_R',(.55,-.20,.81));aim('Hand_R',(.3,-.1,.95))
aim('Thigh_L',(.15,-.34,-.93));aim('Shin_L',(0,.32,-.95))
aim('Thigh_R',(.30,-.62,-.72));aim('Shin_R',(.03,.70,-.72))
aim('Foot_L',(-.35,-.90,-.20));aim('Foot_R',(.10,-.95,-.28))
def bound_regions():
    minima={};all_min=10;points=[]
    for level in range(3):
        obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
        try:
            for v in m.vertices:
                point=ev.matrix_world@v.co;all_min=min(all_min,point.z)
                if level==0:
                    points.append(point.copy());weights=[(g.weight,obj.vertex_groups[g.group].name) for g in v.groups];name=max(weights)[1]
                    minima[name]=min(minima.get(name,10),point.z)
        finally:ev.to_mesh_clear()
    return all_min,minima,points
before=bound_regions();world_up=hip.bone.matrix_local.to_3x3().inverted()@Vector((0,0,1));offset=.002-before[0];hip.location+=world_up*offset;bpy.context.view_layer.update();after=bound_regions()
bpy.data.collections['ApexR2_ContactReferenceOnly'].hide_render=True
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
camera=scene.camera;camera.data.type='ORTHO';low=Vector(tuple(min(p[a] for p in after[2]) for a in range(3)));high=Vector(tuple(max(p[a] for p in after[2]) for a in range(3)));target=(low+high)*.5;camera.location=target+Vector((2.2,-4.6,1.3));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=max(high.x-low.x,high.y-low.y,high.z-low.z)*1.35
scene.render.filepath=ROOT+'docs/p08/golden/ash/v7r2/trial-end-02.png';bpy.ops.render.render(write_still=True)
print('V7R2_TRIAL_END '+json.dumps({'sourceSaved':False,'actionsEdited':False,'worldVerticalShift':offset,'beforeMinimum':before[0],'afterMinimum':after[0],'regionMinima':after[1],'render':scene.render.filepath,'visualAccepted':False}))
