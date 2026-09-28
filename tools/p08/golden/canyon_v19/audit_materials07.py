"""Read frozen06/07 material graphs and exact packed image bytes, without saves."""
import bpy,json
root='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/V19/'
parent=root+'RB_Golden_Canyon_V19_06.blend';candidate=root+'RB_Golden_Canyon_V19_07.blend'
if bpy.data.filepath.replace('\\','/')!=candidate:raise RuntimeError('Expected owned saved07.')
def snapshot():
    materials={};images={}
    for material in bpy.data.materials:
        nodes=[];links=[]
        if material.use_nodes:
            for node in material.node_tree.nodes:
                inputs=[]
                for socket in node.inputs:
                    if socket.type in {'VALUE','INT','BOOLEAN'}:inputs.append((socket.name,float(socket.default_value)))
                    elif socket.type in {'VECTOR','RGBA'}:inputs.append((socket.name,list(socket.default_value)))
                    elif socket.type=='STRING':inputs.append((socket.name,socket.default_value))
                image=node.image if node.type in {'TEX_IMAGE','TEX_ENVIRONMENT'} else None
                nodes.append((node.name,node.type,inputs,image.name if image else None))
                if image:
                    packed=bytes(image.packed_file.data) if image.packed_file else None
                    images[image.name]=(image.filepath,list(image.size),image.source,image.colorspace_settings.name,image.alpha_mode,packed)
            links=[(link.from_node.name,link.from_socket.name,link.to_node.name,link.to_socket.name) for link in material.node_tree.links]
        materials[material.name]=(list(material.diffuse_color),material.roughness,material.metallic,material.use_nodes,nodes,links)
    return materials,images
try:
    bpy.ops.wm.open_mainfile(filepath=parent);before_materials,before_images=snapshot()
    bpy.ops.wm.open_mainfile(filepath=candidate);after_materials,after_images=snapshot()
    changed_materials=[name for name in set(before_materials)|set(after_materials) if before_materials.get(name)!=after_materials.get(name)]
    changed_images=[name for name in set(before_images)|set(after_images) if before_images.get(name)!=after_images.get(name)]
    result={'parent':parent,'candidate':candidate,'materialCount':len(before_materials),'linkedImageCount':len(before_images),
        'packedBytesCompared':sum(len(row[5]) for row in before_images.values() if row[5] is not None),
        'changedMaterials':changed_materials,'changedImages':changed_images,'passed':not changed_materials and not changed_images,
        'scope':'Exact packed image bytes and used material graph/core values; both source files loaded from disk, never saved.'}
finally:
    if bpy.data.filepath.replace('\\','/')!=candidate:bpy.ops.wm.open_mainfile(filepath=candidate)
print('CANYON_V19_MATERIALS07 '+json.dumps(result))
if not result['passed']:raise RuntimeError('Original material/image source changed.')
