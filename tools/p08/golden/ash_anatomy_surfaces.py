"""Apply provenance-bound CC0 anatomy surfaces for likeness diagnosis.

Actual 3D render only; no concept pixels, model substitution or addon code.
"""
import bpy,json
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
OUT=ROOT+'ArtSource/P08/Golden/Ash/AnatomyV1/'
assert 'Ash/AnatomyV1/' in bpy.data.filepath.replace('\\','/')
body=bpy.data.objects['RB_Ash_AnatomicalBase_CC0_Derivative']
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)

def material(name,image_path,roughness,alpha=False):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF')
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(image_path,check_existing=True);tex.image.pack()
    links.new(tex.outputs['Color'],shader.inputs['Base Color'])
    shader.inputs['Roughness'].default_value=roughness
    if alpha:links.new(tex.outputs['Alpha'],shader.inputs['Alpha'])
    return mat,shader

skin,shader=material('Ash_Anatomy_SkinReference_CC0',OUT+'ReferenceSurfaces/young_lightskinned_male_diffuse.png',.51)
shader.inputs['Subsurface Weight'].default_value=.06
shader.inputs['Subsurface Radius'].default_value=(1,.5,.25)
shader.inputs['Subsurface Scale'].default_value=.013
nodes=skin.node_tree.nodes;links=skin.node_tree.links
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=340;noise.inputs['Detail'].default_value=2
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.10;bump.inputs['Distance'].default_value=.00025
links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
body.data.materials.clear();body.data.materials.append(skin)
for kind,texture,roughness in [('Eyes','brown_eye.png',.22),('Brows','eyebrow001.png',.58)]:
    bpy.ops.wm.obj_import(filepath=OUT+'RB_Ash_Anatomy_'+kind+'.obj',forward_axis='NEGATIVE_Z',up_axis='Y',use_split_objects=False,use_split_groups=False)
    obj=bpy.context.object;obj.name='RB_Ash_Anatomy_'+kind+'_CC0_Derivative'
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    mat,shader=material('Ash_Anatomy_'+kind+'_Reference_CC0',OUT+'ReferenceSurfaces/'+texture,roughness,kind=='Brows')
    obj.data.materials.clear();obj.data.materials.append(mat)
    for polygon in obj.data.polygons:polygon.use_smooth=True
    if kind=='Eyes':
        shader.inputs['Coat Weight'].default_value=.4
        mod=obj.modifiers.new('Eyes anatomical preview','SUBSURF');mod.levels=2;mod.render_levels=2

scene=bpy.context.scene
for obj in scene.objects:
    if obj.type=='LIGHT':obj.data.energy*=.22
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
scene.cycles.samples=40
scene.camera.data.ortho_scale=.44
for name,position,target in [
    ('front',(0,-3,1.60),(0,0,1.60)),
    ('three-quarter',(.65,-2.0,1.65),(0,-.005,1.60)),
    ('profile',(3,0,1.61),(0,0,1.60)),
]:
    scene.camera.location=position;scene.camera.rotation_euler=(Vector(target)-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=ROOT+'docs/p08/golden/recovery/ash-anatomy-'+name+'.png'
    bpy.ops.render.render(write_still=True)
    print('ASH_ANATOMY_RENDERED '+scene.render.filepath)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=OUT+'RB_Ash_AnatomyV1.blend')
print(json.dumps({'status':'unaccepted-likeness-foundation','body_dimensions':list(body.dimensions),
                  'addon_registered':False,'scene':bpy.data.filepath}))
