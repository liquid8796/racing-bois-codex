import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
assert '/Garage/V5/' in bpy.data.filepath.replace('\\','/')
rows=[]
for name,weight,rough,normal in [('Garage_Floor',.75,.18,.30),('Garage_PowderSteel',.10,.28,1.0),('Garage_HelmetShell',.80,.10,1.0)]:
    material=bpy.data.materials[name];bs=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Coat Weight'].default_value=weight;bs.inputs['Coat Roughness'].default_value=rough;bs.inputs['Coat IOR'].default_value=1.5
    bs.inputs['IOR'].default_value=1.5
    for node in material.node_tree.nodes:
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=normal
    rows.append({'name':name,'coatWeight':weight,'coatRoughness':rough,'coatIor':1.5,'baseNormalStrength':normal,
        'baseRoughnessAndMetallicTextureUnchanged':True,'unityShader':'Universal Render Pipeline/Complex Lit',
        'unityClearCoatMask':weight,'unityClearCoatSmoothness':1-rough,'unityNormalScale':normal})
packed=[]
used=set()
for o in bpy.data.objects['RB_Golden_Garage'].children_recursive:
    if o.type=='MESH':
        for material in o.data.materials:
            if material and material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type=='TEX_IMAGE' and node.image is not None:used.add(node.image)
for image in used:
    assert image.source=='FILE' and not image.is_dirty,'Do not discard an unsaved image bake'
    image.reload(); image.pack()
    # Non-cryptographic packed-byte fingerprint, cross-checked against the
    # external PNG in the receipt writer alongside an external SHA256.
    fingerprint=14695981039346656037
    data=image.packed_file.data
    for value in data:fingerprint=((fingerprint^value)*1099511628211)&18446744073709551615
    packed.append({'name':image.name,'filepath':bpy.path.abspath(image.filepath),'bytes':len(data),'packedFnv1a64':format(fingerprint,'016x')})
scene=bpy.context.scene;scene.render.filepath=ROOT+'docs/p08/golden/garage/v5/coated-floor.png'
scene.cycles.samples=48
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage.blend')
print('GARAGE_V5_MATERIAL '+json.dumps({'materials':rows,'packedImages':packed,'texturesEdited':False,'geometryEdited':False,'visualAccepted':False}))
