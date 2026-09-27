"""Actual geometry atlas for each equipment LOD, preserving all old body UVs."""
import bpy,math,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
equipment=bpy.data.collections['AshV6_Equipment'];source=bpy.data.collections.new('AshV6_Equipment_Source');bpy.context.scene.collection.children.link(source)
replacement={}
# Retain the authored, localized enamel wear as the source, but evaluate it
# on the current shell's true rest positions and rebake its new atlas.
enamel=bpy.data.materials['AshV4_HelmetEnamel_Source'].copy();enamel.name='AshV6_Enamel_Source';enamel.use_fake_user=True
replacement['AshV4_HelmetEnamel_Baked']=enamel
for old,role in [('AshV6_HarnessLeather','HarnessLeather'),('AshV6_OpticalGasket','OpticalGasket'),('AshV6_FrameBronze','FrameBronze'),('AshV6_DarkFastener','DarkFastener')]:
 mat=bpy.data.materials[old];mat.use_fake_user=True
 if role=='HarnessLeather':
  nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF'];tex=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=420;noise.inputs['Detail'].default_value=2;links.new(tex.outputs['Object'],noise.inputs['Vector'])
  bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.00012;links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
# Amber is represented as tinted, polished opaque optics in this candidate;
# there is no claim of transmission parity with the concept's glass.
optic=bpy.data.materials.new('AshV6_AmberOptic_Source');optic.use_nodes=True;bs=optic.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.18,.065,.012,1);bs.inputs['Roughness'].default_value=.22;bs.inputs['Metallic'].default_value=0
replacement['AshV2_AmberLens_Baked']=optic
rows=[]
for level in range(3):
 parts=[o for o in equipment.objects if o.name.startswith('AshV6_L'+str(level)+'_')]
 for obj in parts:
  attr=obj.data.attributes.get('AshV4_RestMeters') or obj.data.attributes.new('AshV4_RestMeters','FLOAT_VECTOR','POINT')
  for v in obj.data.vertices:attr.data[v.index].vector=v.co
  for i,mat in enumerate(obj.data.materials):
   if mat.name in replacement:obj.data.materials[i]=replacement[mat.name]
  backup=obj.copy();backup.data=obj.data.copy();source.objects.link(backup);backup.name='Authored_'+obj.name
  backup.hide_render=True;backup.hide_set(True)
 bpy.ops.object.select_all(action='DESELECT')
 for obj in parts:obj.hide_set(False);obj.select_set(True)
 active=parts[0];bpy.context.view_layer.objects.active=active;bpy.ops.object.join();active.name='AshV6_L'+str(level)+'_Equipment'
 for mod in list(active.modifiers):active.modifiers.remove(mod)
 while len(active.data.uv_layers)>1:active.data.uv_layers.remove(active.data.uv_layers[-1])
 active.data.uv_layers[0].name='UV0';active.data.uv_layers.active_index=0
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.151917,island_margin=.006,area_weight=0,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
 active['atlas_resolution']=[2048,1024,512][level]
 active.data.calc_loop_triangles();rows.append({'lod':level,'vertices':len(active.data.vertices),'triangles':len(active.data.loop_triangles),'textureSize':active['atlas_resolution'],'sourceMaterials':[m.name for m in active.data.materials]})
 active.hide_render=level!=0;active.hide_set(level!=0)
source.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6_AtlasSource.blend',compress=False)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_ATLAS_SOURCE '+json.dumps({'lods':rows,'bodyUvUnchanged':True,'sourceEquipmentPreserved':True,'noTransmissionClaim':True,'visualAccepted':False}))
