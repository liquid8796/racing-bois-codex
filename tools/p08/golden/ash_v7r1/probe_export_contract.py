import bpy,json
properties=bpy.ops.export_scene.fbx.get_rna_type().properties
rows=[]
for p in properties:
    if 'tri' in p.identifier.lower() or 'mesh' in p.identifier.lower():
        rows.append({'name':p.identifier,'type':p.type,'description':p.description})
print('FBX_EXPORT_CONTRACT '+json.dumps({'file':bpy.data.filepath,'properties':rows,'saved':False}))
