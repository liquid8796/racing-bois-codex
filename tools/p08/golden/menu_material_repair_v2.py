import bpy,json,math
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/MenuEnvironment/V1/RB_Golden_MenuEnvironment.blend',load_ui=False,use_scripts=False)
root=bpy.data.objects['RB_Golden_MenuEnvironment'];rows=[]
for identity in ['Menu_L0_EdgeStone_12','Menu_L0_EdgeStone_13']:
    old=bpy.data.objects[identity];mesh=old.data;mesh.calc_loop_triangles();expected=len(mesh.loop_triangles);count=0
    assert len(mesh.materials)==2 and all(m is not None for m in mesh.materials),identity
    for slot,material in enumerate(mesh.materials):
        polys=[poly for poly in mesh.polygons if poly.material_index==slot]
        assert polys and all(len(poly.vertices)==3 for poly in polys),identity
        used=sorted({index for poly in polys for index in poly.vertices});remap={index:n for n,index in enumerate(used)}
        faces=[tuple(remap[index] for index in poly.vertices) for poly in polys]
        wanted_normals=[tuple(mesh.corner_normals[loop].vector) for poly in polys for loop in poly.loop_indices]
        name=identity+'_'+material.name.replace('Canyon_','')
        data=bpy.data.meshes.new(name);data.from_pydata([tuple(mesh.vertices[index].co) for index in used],[],faces);data.update();data.materials.append(material)
        for face,source in zip(data.polygons,polys):face.material_index=0;face.use_smooth=source.use_smooth
        for original in mesh.uv_layers:
            layer=data.uv_layers.new(name=original.name,do_init=False)
            values=[tuple(original.data[loop].uv) for poly in polys for loop in poly.loop_indices]
            for i,value in enumerate(values):layer.data[i].uv=value
            assert all(tuple(item.uv)==value for item,value in zip(layer.data,values)),name
        obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj);obj.parent=root;obj.matrix_world=old.matrix_world.copy()
        data.normals_split_custom_set(wanted_normals);data.update()
        deviation=0
        for wanted,actual in zip(wanted_normals,data.corner_normals):
            a=Vector(wanted);b=actual.vector;deviation=max(deviation,math.degrees(math.atan2(a.cross(b).length,a.dot(b))))
        assert all(tuple(data.vertices[remap[index]].co)==tuple(mesh.vertices[index].co) for index in used),name
        obj.hide_set(False);obj.hide_render=False;count+=len(data.polygons)
        rows.append({'sourceObject':identity,'object':name,'material':material.name,'triangles':len(data.polygons),'unusedVertices':len(data.vertices)-len({i for p in data.polygons for i in p.vertices}),
          'positionsUvMaterialIdentityPreserved':True,'maximumNormalEncodingDeviationDegrees':deviation})
    assert count==expected,identity
    bpy.data.objects.remove(old,do_unlink=True)
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    assert obj.material_slots and all(slot.material is not None and slot.link=='DATA' for slot in obj.material_slots),obj.name
    assert all(0<=poly.material_index<len(obj.material_slots) for poly in obj.data.polygons),obj.name
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/MenuEnvironment/V2/RB_Golden_MenuEnvironment.blend')
print('MENU_V2_MATERIAL_REPAIR '+json.dumps({'objects':rows,'sourceV1Unchanged':True,'scope':'Two affectedLOD0 meshes split by existing material only; no default/fallback material and no geometry redesign.'}))
