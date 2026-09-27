"""Bind the current disk textures after live Blender cached earlier revisions."""
import bpy,json
root=bpy.data.objects['RB_Golden_Canyon']
images=set()
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    for material in obj.data.materials:
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type=='TEX_IMAGE' and node.image:images.add(node.image)
result=[]
for image in images:
    before=list(image.pixels[:4]);image.reload();image.pack()
    result.append({'name':image.name,'path':image.filepath,'beforeFirstPixel':before,'afterFirstPixel':list(image.pixels[:4])})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/RB_Golden_Canyon.blend')
print('CANYON_TEXTURE_REFRESH '+json.dumps(result))
