import bpy,json
obj=bpy.data.objects['AshV3_L0_Skin'];report=[]
for mat in obj.data.materials:
    if not any(role in mat.name for role in ['BootLeather','Rubber']):continue
    images=[]
    for node in mat.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image:
            images.append({'node':node.name,'image':node.image.name,'path':node.image.filepath,'source':node.image.source,'hasData':node.image.has_data,'packed':bool(node.image.packed_file),'outputs':[link.to_node.name+':'+link.to_socket.name for output in node.outputs for link in output.links]})
    report.append({'material':mat.name,'images':images})
print('V3_RUNTIME_MATERIAL_BINDINGS '+json.dumps(report))
