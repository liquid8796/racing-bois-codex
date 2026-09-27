"""Actual Ash V2 source renders; no concept pixels are composited into output."""
import bpy,json
from mathutils import Vector
scene=bpy.context.scene
for obj in list(scene.objects):
    if obj.type in ['LIGHT','CAMERA'] or obj.name=='AshV2_ReviewFloor':bpy.data.objects.remove(obj,do_unlink=True)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('AshV2 studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.20,.21,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45;scene.world=world
floor=bpy.data.materials.new('AshV2_ReviewFloorOnly');floor.use_nodes=True
floor.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.18,.19,.20,1)
floor.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,-.008));obj=bpy.context.object;obj.name='AshV2_ReviewFloor';obj.data.materials.append(floor)
for name,pos,power,size in [('Key',(-2.4,-3.5,3.8),420,3),('Fill',(2.5,-1.5,2.5),170,2.8),('Rim',(.5,2.1,3),450,2.1)]:
    light=bpy.data.lights.new('AshV2_'+name,'AREA');obj=bpy.data.objects.new('AshV2_'+name,light);scene.collection.objects.link(obj)
    obj.location=pos;light.energy=power;light.size=size
    obj.rotation_euler=(Vector((0,0,1.1))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('AshV2_ReviewCamera');camera=bpy.data.objects.new('AshV2_ReviewCamera',data);scene.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO'
for name,position,target,scale,resolution in [
    ('body-front',(0,-4,1.02),(0,0,.96),2.08,(900,1300)),
    ('face',(0,-3,1.664),(0,-.045,1.664),.44,(1100,1100)),
    ('body-three-quarter',(3,-5,1.9),(0,0,.96),2.12,(1100,1400)),
    ('side',(4,-.02,1.04),(0,-.02,.96),2.07,(900,1300)),
]:
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=resolution
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v2/ash-'+name+'.png'
    bpy.ops.render.render(write_still=True)
    print('ASH_V2_RENDER '+scene.render.filepath)
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print('ASH_V2_REVIEW_SAVED')
