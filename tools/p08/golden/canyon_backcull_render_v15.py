"""Diagnostic camera render that removes opaque backfaces rather than relying on Cycles' two-sided defaults."""
import bpy
scene=bpy.context.scene
changes=[]
for material in bpy.data.materials:
    if not material.name.startswith('Canyon_') or material.name in ['Canyon_Sage','Canyon_DryGrass'] or not material.use_nodes:continue
    output=next((n for n in material.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None)
    if output is None or not output.inputs['Surface'].links:continue
    original=output.inputs['Surface'].links[0].from_socket
    nodes=material.node_tree.nodes;links=material.node_tree.links
    geometry=nodes.new('ShaderNodeNewGeometry');transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader')
    links.new(geometry.outputs['Backfacing'],mix.inputs[0]);links.new(original,mix.inputs[1]);links.new(transparent.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],output.inputs['Surface'])
    changes.append((material,output,original,geometry,transparent,mix))
try:
    scene.render.threads_mode='FIXED';scene.render.threads=4;scene.cycles.device='CPU';scene.cycles.samples=16
    scene.render.resolution_x=1536;scene.render.resolution_y=768;scene.render.resolution_percentage=75
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v15/backcull-gameplay.png'
    bpy.ops.render.render(write_still=True)
finally:
    for material,output,original,geometry,transparent,mix in changes:
        material.node_tree.links.new(original,output.inputs['Surface'])
        for node in [geometry,transparent,mix]:material.node_tree.nodes.remove(node)
print('CANYON_BACKCULL_DIAGNOSTIC_RENDERED; material graphs restored; no source saved')
