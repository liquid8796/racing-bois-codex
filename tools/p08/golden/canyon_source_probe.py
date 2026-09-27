import bpy,json
root='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/SourceModels/'
result=[]
for slug in ['namaqualand_cliff_01','namaqualand_cliff_02']:
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=root+slug+'/'+slug+'_fbx.fbx',use_anim=False)
    for obj in set(bpy.data.objects)-before:
        if obj.type=='MESH':
            result.append({'slug':slug,'name':obj.name,'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons),'dimensions':list(obj.dimensions),'location':list(obj.location),'rotation':list(obj.rotation_euler),'bounds':[[min(v.co[i] for v in obj.data.vertices),max(v.co[i] for v in obj.data.vertices)] for i in range(3)],'materials':[m.name for m in obj.data.materials]})
        obj.hide_render=True;obj.hide_set(True)
print('CC0_GEOMETRY_PROBE '+json.dumps(result))
