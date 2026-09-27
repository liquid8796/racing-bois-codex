import bpy,json,math
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
assert '/Garage/V5/' in bpy.data.filepath.replace('\\','/')
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage_CoatComparison.blend')
# Baseline V5 repairs UV data only. The coat trial is retained independently
# and is not silently promoted as a workaround for native lighting parity.
for name,normal in [('Garage_Floor',.55),('Garage_PowderSteel',1.0),('Garage_HelmetShell',1.0)]:
    m=bpy.data.materials[name];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Coat Weight'].default_value=0;bs.inputs['Coat Roughness'].default_value=.03;bs.inputs['Coat IOR'].default_value=1.5
    for node in m.node_tree.nodes:
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=normal
scene=bpy.context.scene;scene.render.filepath=ROOT+'docs/p08/golden/garage/v5/uv-final-original-materials.png'
lights=[]
def unity(v):return [v.x,v.z,v.y]
for o in bpy.data.objects:
    if o.type!='LIGHT':continue
    light=o.data
    normal=o.matrix_world.to_3x3()@Vector((0,0,-1))
    width_axis=o.matrix_world.to_3x3()@Vector((1,0,0));height_axis=o.matrix_world.to_3x3()@Vector((0,1,0))
    lights.append({'name':o.name,'type':light.type,'shape':getattr(light,'shape',None),
        'positionUnity':unity(o.matrix_world.translation),'frontNormalUnity':unity(normal),
        'widthAxisUnity':unity(width_axis),'heightAxisUnity':unity(height_axis),
        'sizeMetres':getattr(light,'size',None),'sizeYMetres':getattr(light,'size_y',None),
        'powerWatts':light.energy,'colorLinear':list(light.color),
        'diffuseFactor':light.diffuse_factor,'specularFactor':light.specular_factor,
        'spreadRadians':getattr(light,'spread',None),'normalize':getattr(light,'normalize',None)})
lamp=bpy.data.materials['Garage_Lamp'];bs=next(n for n in lamp.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
emission_nodes=[]
for link in lamp.node_tree.links:
    if link.to_node==bs and link.to_socket.name=='Emission Color':
        emission_nodes.append({'image':link.from_node.image.name,'file':bpy.path.abspath(link.from_node.image.filepath),'colorSpace':link.from_node.image.colorspace_settings.name})
lighting={'lights':lights,'emissionStrength':bs.inputs['Emission Strength'].default_value,'emissionNodes':emission_nodes,
    'camera':{'positionUnity':unity(scene.camera.location),'rotationBlenderRadians':list(scene.camera.rotation_euler),'focalLengthMm':scene.camera.data.lens,'sensorWidthMm':scene.camera.data.sensor_width},
    'colorManagement':{'viewTransform':scene.view_settings.view_transform,'look':scene.view_settings.look,'exposure':scene.view_settings.exposure,'gamma':scene.view_settings.gamma},
    'scope':'Actual authored Blender source values. Cycles includes direct area-light specular. Unity baked rectangles/cubemap capture are not numerically equivalent; calibrate actual native pixels without altering baseline UV-only materials.'}
root=bpy.data.objects['RB_Golden_Garage'];states=[]
bpy.ops.object.select_all(action='DESELECT')
for o in root.children_recursive:
    states.append((o,o.hide_get(),o.hide_render));o.hide_set(False);o.hide_render=False;o.select_set(True)
root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=ROOT+'_local/p08-garage-v5-staging/RB_Golden_Garage.fbx',use_selection=True,object_types={'EMPTY','MESH'},axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=True)
for o,hidden,render_hidden in states:o.hide_set(hidden);o.hide_render=render_hidden
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage.blend')
print('GARAGE_V5_EXPORT '+json.dumps({'fbx':'_local/p08-garage-v5-staging/RB_Golden_Garage.fbx','source':'ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage.blend','defaultMaterials':'original V4 parameters, repaired primary UVs','lighting':lighting,'visualAccepted':False}))
