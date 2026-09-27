"""Import CC0-derived anatomical OBJ through safe-mode Blender MCP.

This uses only the expressly supported OBJ import and ordinary mesh/render
operations. No MPFB addon is registered or executed.
"""
import bpy,bmesh,json
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
OUT=ROOT+'ArtSource/P08/Golden/Ash/AnatomyV1/'
scene=bpy.context.scene
assert 'Apex/V7/' in bpy.data.filepath.replace('\\','/')
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.wm.obj_import(filepath=OUT+'RB_Ash_AnatomicalBase.obj',forward_axis='NEGATIVE_Z',up_axis='Y',use_split_objects=False,use_split_groups=False)
body=bpy.context.object
body.name='RB_Ash_AnatomicalBase_CC0_Derivative'
body['provenance']='MakeHuman core base and targets CC0; see adjacent provenance.json. Not final Ash.'
body['acceptance']='unaccepted-anatomical-base'
for face in body.data.polygons:face.use_smooth=True
material=bpy.data.materials.new('Ash_Anatomy_Clay_NotProduction');material.use_nodes=True
shader=material.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value=(.33,.31,.28,1)
shader.inputs['Roughness'].default_value=.56
body.data.materials.clear();body.data.materials.append(material)
modifier=body.modifiers.new('Anatomical surface preview','SUBSURF');modifier.levels=1;modifier.render_levels=1
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=900;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('Ash anatomical review world');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.16,.17,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.6;scene.world=world
for name,location,power,size in [('Key',(-1.3,-2,2.5),300,2.1),('Fill',(1.4,-.6,1.9),120,1.3),('Rim',(.4,1.2,2.3),220,1.3)]:
    light=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj)
    obj.location=location;light.energy=power;light.size=size
    obj.rotation_euler=(Vector((0,0,1.60))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Ash anatomy camera');camera=bpy.data.objects.new('Ash anatomy camera',data);scene.collection.objects.link(camera);scene.camera=camera
data.type='ORTHO';data.ortho_scale=.48
camera.location=(0,-3,1.58);camera.rotation_euler=(Vector((0,0,1.58))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=ROOT+'docs/p08/golden/recovery/ash-anatomy-clay-front.png'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'RB_Ash_AnatomyV1.blend')
print(json.dumps({'import':'success','vertices':len(body.data.vertices),'faces':len(body.data.polygons),'dimensions':list(body.dimensions),'status':'unaccepted-anatomical-base','addon_registered':False}))
bpy.ops.render.render(write_still=True)
print('ANATOMY_CLAY_RENDERED '+scene.render.filepath)
