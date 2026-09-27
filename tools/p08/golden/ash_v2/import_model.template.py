"""Create the complete Ash candidate foundation with an anatomical Generic rig.

J, VERTEX_PROBES and counts are immutable numeric header data prepended by the
data preparation tool. Run the composed import_model.py via direct Blender MCP.
"""
import bpy,bmesh,math,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
SOURCE=ROOT+'ArtSource/P08/Golden/Ash/V2/'
scene=bpy.context.scene
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for previous in list(bpy.data.actions):
    if previous.name.startswith('RB_'):bpy.data.actions.remove(previous)
root=bpy.data.objects.new('RB_Golden_Ash_V2',None);scene.collection.objects.link(root)
def cv(p):return Vector((p[0],-p[2],p[1]))
spec=[('Hip',J['joint-pelvis'],J['joint-spine-4'],None),
      ('Torso',J['joint-spine-4'],J['joint-neck'],'Hip'),
      ('Head',J['joint-neck'],J['joint-head-2'],'Torso')]
for side in ['L','R']:
    lower=side.lower()
    spec.extend([
      ('UpperArm_'+side,J['joint-'+lower+'-shoulder'],J['joint-'+lower+'-elbow'],'Torso'),
      ('Forearm_'+side,J['joint-'+lower+'-elbow'],J['joint-'+lower+'-hand'],'UpperArm_'+side),
      ('Hand_'+side,J['joint-'+lower+'-hand'],J['joint-'+lower+'-finger-3-3'],'Forearm_'+side),
      ('Thigh_'+side,J['joint-'+lower+'-upper-leg'],J['joint-'+lower+'-knee'],'Hip'),
      ('Shin_'+side,J['joint-'+lower+'-knee'],J['joint-'+lower+'-ankle'],'Thigh_'+side),
      ('Foot_'+side,J['joint-'+lower+'-ankle'],J['joint-'+lower+'-toe-1-3'],'Shin_'+side)])
data=bpy.data.armatures.new('AshV2_AnatomicalRig')
rig=bpy.data.objects.new('RB_P06_Rider_Rig',data);scene.collection.objects.link(rig);rig.parent=root
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,head,tail,parent in spec:
    bone=data.edit_bones.new('RB_P06_Rider_L0_'+name);bone.head=cv(head);bone.tail=cv(tail)
    if parent:bone.parent=data.edit_bones['RB_P06_Rider_L0_'+parent]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
rig['clip_contract']='12 matching retargeted Ash clips required; old P06 translation curves must not be used.'

def mapped_material(name,path,roughness,tint=(1,1,1),normal=None,alpha=False,metallic=0):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=roughness;shader.inputs['Metallic'].default_value=metallic
    if path:
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(SOURCE+'Inputs/'+path,check_existing=True);tex.image.pack()
        multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1;multiply.inputs[2].default_value=(*tint,1)
        links.new(tex.outputs['Color'],multiply.inputs[1]);links.new(multiply.outputs[0],shader.inputs['Base Color'])
        if alpha:links.new(tex.outputs['Alpha'],shader.inputs['Alpha'])
    else:shader.inputs['Base Color'].default_value=(*tint,1)
    if normal:
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(SOURCE+'Inputs/'+normal,check_existing=True);tex.image.colorspace_settings.name='Non-Color';tex.image.pack()
        node=nodes.new('ShaderNodeNormalMap');node.inputs['Strength'].default_value=.55
        links.new(tex.outputs['Color'],node.inputs['Color']);links.new(node.outputs['Normal'],shader.inputs['Normal'])
    return mat
materials={
 'Body':mapped_material('AshV2_Skin','young_lightskinned_male_diffuse.png',.52,(.76,.61,.47)),
 'Eyes':mapped_material('AshV2_Eyes','brown_eye.png',.18,(.58,.51,.44)),
 'Brows':mapped_material('AshV2_Brows','eyebrow001.png',.6,(.23,.15,.10),alpha=True),
 'Hair':mapped_material('AshV2_Hair','short02_diffuse.png',.62,(.18,.12,.085),'short02_normal.png',True),
 'Clothes':mapped_material('AshV2_CharcoalLeather',None,.56,(.034,.030,.026),'male_casualsuit02_normal.png'),
 'Shoes':mapped_material('AshV2_BootLeather',None,.53,(.12,.065,.032),'shoes01_normal.png'),
}
materials['Body'].node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value=.045
materials['Eyes'].node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.35
for kind,count in COUNTS.items():
    bpy.ops.wm.obj_import(filepath=SOURCE+'Inputs/'+kind+'.obj',forward_axis='NEGATIVE_Z',up_axis='Y',use_split_objects=False,use_split_groups=False)
    obj=bpy.context.object;obj.name='AshV2_'+kind
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    assert len(obj.data.vertices)==count,(kind,len(obj.data.vertices),count)
    for index,expected in VERTEX_PROBES[kind]:
        assert (obj.data.vertices[index].co-cv(expected)).length<.000001,(kind,index,'OBJ vertex index mapping changed')
    obj.parent=rig
    for polygon in obj.data.polygons:polygon.use_smooth=True
    obj.data.materials.clear();obj.data.materials.append(materials[kind])
    obj['provenance']='Licensed MakeHuman CC0 static data derivative; see V2/provenance.json. Custom Ash candidate, unaccepted.'
    if kind not in ['Brows','Hair']:
        modifier=obj.modifiers.new('Sculpt surface subdivision','SUBSURF');modifier.levels=1;modifier.render_levels=1
    deform=obj.modifiers.new('Ash anatomical Generic deformation','ARMATURE');deform.object=rig;deform.use_deform_preserve_volume=False
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
bpy.ops.wm.save_as_mainfile(filepath=SOURCE+'RB_Golden_Ash_V2.blend')
print(json.dumps({'imported':list(COUNTS),'rig_bones':len(rig.data.bones),'productionAccepted':False}))
