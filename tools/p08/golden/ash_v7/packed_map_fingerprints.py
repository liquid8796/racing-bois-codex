import bpy,json
images=set()
materials=set(m for level in range(3) for m in bpy.data.objects['AshV7_L'+str(level)+'_Skin'].data.materials)
for mat in materials:
    for node in mat.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image is not None:images.add(node.image)
rows=[]
for image in images:
    assert image.source=='FILE' and image.packed_file is not None
    data=image.packed_file.data;fingerprint=14695981039346656037
    for byte in data:fingerprint=((fingerprint^byte)*1099511628211)&18446744073709551615
    rows.append({'name':image.name,'path':bpy.path.abspath(image.filepath),'bytes':len(data),'packedFnv1a64':format(fingerprint,'016x'),'colorSpace':image.colorspace_settings.name})
print('ASH_V7_PACKED_IMAGES '+json.dumps({'images':rows,'scope':'Packed bytes fingerprint, not a visual acceptance claim.'}))
