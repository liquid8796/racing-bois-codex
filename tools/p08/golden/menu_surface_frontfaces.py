import bpy,json
root=bpy.data.objects['RB_Golden_MenuEnvironment'];rows=[]
for obj in root.children_recursive:
    if obj.type!='MESH' or not any(token in obj.name for token in ['_Road_','_Shoulder_','_WhitePaint_','_YellowPaint_','_Pullout','_EdgeGravel','_NearValley','_FarValley']):continue
    old=obj.data;old.calc_loop_triangles();faces=[];corners=[];normals=[];flipped=0
    for tri in old.loop_triangles:
        indices=list(tri.vertices);loops=list(tri.loops)
        a,b,c=[old.vertices[i].co for i in indices];negative=(b-a).cross(c-a).z<0
        if negative:indices.reverse();loops.reverse();flipped+=1
        faces.append(indices);corners.extend(loops)
        for loop in loops:
            value=old.corner_normals[loop].vector;normals.append(tuple(-value if negative else value))
    new=bpy.data.meshes.new(old.name+'_FrontUp');new.from_pydata([tuple(v.co) for v in old.vertices],[],faces);new.update()
    for material in old.materials:new.materials.append(material)
    for face,source in zip(new.polygons,old.polygons):face.material_index=source.material_index;face.use_smooth=source.use_smooth
    for source in old.uv_layers:
        uv=new.uv_layers.new(name=source.name,do_init=False)
        for i,loop in enumerate(corners):uv.data[i].uv=source.data[loop].uv
    obj.data=new;new.normals_split_custom_set(normals);new.update()
    assert all(poly.normal.z>0 for poly in new.polygons),obj.name
    rows.append({'name':obj.name,'triangles':len(new.polygons),'flippedUpward':flipped})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/MenuEnvironment/V1/RB_Golden_MenuEnvironment.blend')
print('MENU_FRONT_FACES '+json.dumps({'objects':rows,'correctedTriangles':sum(r['flippedUpward'] for r in rows),'scope':'Explicit geometric winding on open heightfield/road/paint surfaces. No CullOff workaround.'}))
