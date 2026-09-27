"""Separate unique clothing bake UVs from shared small leather finishes."""
import bpy,math
from mathutils import Matrix,Vector
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
clothes=bpy.data.objects['AshV2_Clothes'];black=bpy.data.materials['AshV2_CharcoalLeather']
tailored=black.copy();tailored.name='AshV2_TailoredClothing';clothes.data.materials.clear();clothes.data.materials.append(tailored)
for polygon in clothes.data.polygons:polygon.material_index=0
# A unique bake is necessary: the clothing has a nonuniform stripe atlas;
# other leather pieces intentionally share a small seamless physical finish.
nodes=tailored.node_tree.nodes;links=tailored.node_tree.links;p=nodes['Principled BSDF']
normal=next(n for n in nodes if n.bl_idname=='ShaderNodeNormalMap')
bump=next(n for n in nodes if n.bl_idname=='ShaderNodeBump')
normal.inputs['Strength'].default_value=.80
links.new(normal.outputs['Normal'],bump.inputs['Normal'])
previous=p.inputs['Base Color'].links[0].from_socket
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=39;noise.inputs['Detail'].default_value=5;noise.inputs['Roughness'].default_value=.7
wear=nodes.new('ShaderNodeMixRGB');wear.blend_type='MULTIPLY';wear.inputs[0].default_value=.24
links.new(previous,wear.inputs[1]);links.new(noise.outputs['Fac'],wear.inputs[2]);links.new(wear.outputs[0],p.inputs['Base Color'])
rough=nodes.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.46;rough.inputs['To Max'].default_value=.76
links.new(noise.outputs['Fac'],rough.inputs['Value']);links.new(rough.outputs[0],p.inputs['Roughness'])
nodes=black.node_tree.nodes;links=black.node_tree.links;p=nodes['Principled BSDF']
for link in list(p.inputs['Base Color'].links):links.remove(link)
p.inputs['Base Color'].default_value=(.027,.024,.021,1)
for node in nodes:
    if node.bl_idname=='ShaderNodeNormalMap':node.inputs['Strength'].default_value=0
glass=bpy.data.materials['AshV2_AmberLens'];nodes=glass.node_tree.nodes;links=glass.node_tree.links;p=nodes['Principled BSDF']
for link in list(nodes['Material Output'].inputs['Volume'].links):links.remove(link)
p.inputs['Transmission Weight'].default_value=0;p.inputs['Base Color'].default_value=(.052,.021,.006,1)
p.inputs['Metallic'].default_value=.24;p.inputs['Roughness'].default_value=.19;p.inputs['Coat Weight'].default_value=.75
glass['surface_intent']='Very dark amber coated lens. Opaque approximation for matching URP desktop review; visual acceptance pending.'

# A small manufactured collar snap, seated on the actual cloth/neck contour.
body=bpy.data.objects['AshV2_Body']
hit,point,normal,index=body.ray_cast(Vector((-.049,-1,1.548)),Vector((0,1,0)))
if hit:
    center=point+normal*.008
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0065,depth=.0018,location=center)
    obj=bpy.context.object;obj.name='AshV2_CollarSnap';obj.rotation_euler=normal.to_track_quat('Z','Y').to_euler()
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);obj.parent=rig
    obj.data.materials.append(bpy.data.materials['AshV2_AgedBrass'])
    group=obj.vertex_groups.new(name='RB_P06_Rider_L0_Head');group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Ash anatomical Generic deformation','ARMATURE');mod.object=rig
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print('ASH_V2_PBR_SOURCE_SURFACES_READY_FOR_BAKE')
