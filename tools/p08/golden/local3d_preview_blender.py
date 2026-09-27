"""Actual colored and clay inspection of the unaccepted local trial; preserve Canyon scene."""
import bpy,math,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
old_scene=bpy.context.scene
scene=bpy.data.scenes.new('Local TripoSR Trial Inspection')
bpy.context.window.scene=scene
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=ROOT+'_local/p08-local3d/outputs/apex-grid128/apex-grid128.glb')
objects=list(set(bpy.data.objects)-before)
holder=bpy.data.objects.new('Trial raw Z-up correction',None);scene.collection.objects.link(holder)
for obj in objects:
    if obj.parent is None:obj.parent=holder
holder.rotation_euler.x=-math.pi/2
bpy.context.view_layer.update()
meshes=[obj for obj in objects if obj.type=='MESH']
points=[obj.matrix_world@vertex.co for obj in meshes for vertex in obj.data.vertices]
minimum=Vector([min(p[i] for p in points) for i in range(3)]);maximum=Vector([max(p[i] for p in points) for i in range(3)]);center=(minimum+maximum)*.5
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4;scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('Trial Neutral World');world.use_nodes=True;scene.world=world
background=next(node for node in world.node_tree.nodes if node.type=='BACKGROUND');background.inputs['Color'].default_value=(.22,.22,.22,1);background.inputs['Strength'].default_value=.5
for name,position,energy,size in [('Trial Key',(1.4,-1.1,2.2),230,1.2),('Trial Fill',(-1.4,.9,1.3),90,1.5)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=Vector(position)+center;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=5,location=(center.x,center.y,minimum.z-.003));floor=bpy.context.object;floor.name='Trial Inspection Floor'
floor_material=bpy.data.materials.new('Trial Floor Gray');floor_material.use_nodes=True;shader=next(n for n in floor_material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');shader.inputs['Base Color'].default_value=(.14,.14,.14,1);shader.inputs['Roughness'].default_value=.62;floor.data.materials.append(floor_material)
camera_data=bpy.data.cameras.new('Trial Camera');camera=bpy.data.objects.new('Trial Camera',camera_data);scene.collection.objects.link(camera);scene.camera=camera;camera_data.lens=52
clay=bpy.data.materials.new('Trial Geometry Clay');clay.use_nodes=True;shader=next(n for n in clay.node_tree.nodes if n.type=='BSDF_PRINCIPLED');shader.inputs['Base Color'].default_value=(.43,.45,.47,1);shader.inputs['Roughness'].default_value=.7
original_materials={obj:tuple(obj.data.materials) for obj in meshes}
for name,offset,use_clay in [('color-front',(1.7,0,.22),False),('clay-front',(1.7,0,.22),True),('clay-back',(-1.7,0,.22),True),('clay-threequarter',(1.4,-1.25,.65),True)]:
    for obj in meshes:
        obj.data.materials.clear()
        for material in ([clay] if use_clay else original_materials[obj]):obj.data.materials.append(material)
    camera.location=center+Vector(offset);camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=ROOT+'_local/p08-local3d/outputs/apex-grid128/'+name+'.png'
    bpy.ops.render.render(write_still=True)
bpy.context.window.scene=old_scene
for obj in list(scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.data.scenes.remove(scene)
print('LOCAL3D_BLENDER_INSPECTED '+json.dumps({'views':4,'rawBoundsMin':list(minimum),'rawBoundsMax':list(maximum),'visualAccepted':False,'canyonSceneRestored':True}))
