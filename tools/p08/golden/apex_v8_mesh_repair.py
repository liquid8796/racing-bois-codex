"""Remove collapsed bevel vertices and repair only degenerate UV faces.

This is geometric hygiene, not visual acceptance. Re-export and rehash follow.
"""
import bpy,bmesh,json
root=bpy.data.objects['RB_Golden_Apex_v8']
changed=[]
for obj in root.children_recursive:
    if obj.type!='MESH' or not obj.name.endswith('_Body'):continue
    bm=bmesh.new();bm.from_mesh(obj.data)
    before=len(bm.verts)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-9)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    uv=obj.data.uv_layers.active
    fixed=0
    for face in obj.data.polygons:
        points=[uv.data[i].uv.copy() for i in face.loop_indices]
        area=abs(sum(points[i].x*points[(i+1)%len(points)].y-points[(i+1)%len(points)].x*points[i].y for i in range(len(points))))*.5
        if area<1e-10:
            axis=0
            for candidate in [1,2]:
                if abs(face.normal[candidate])>abs(face.normal[axis]):axis=candidate
            axes=[i for i in range(3) if i!=axis]
            # Recenter each small cap chart to avoid cancellation caused by
            # adding 0.5 to an area only a few float ULPs wide.
            origin=obj.data.vertices[obj.data.loops[face.loop_start].vertex_index].co
            for loop in face.loop_indices:
                p=obj.data.vertices[obj.data.loops[loop].vertex_index].co-origin
                uv.data[loop].uv=(p[axes[0]]*2,p[axes[1]]*2)
            fixed+=1
    changed.append({'name':obj.name,'weldedVertices':before-len(obj.data.vertices),'recenteredSmallFaceCharts':fixed})
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for obj in root.children_recursive:obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath='D:/Project/Unity/racing-bois/Assets/RacingBois/Art/P08/Golden/Apex/V8/RB_Golden_Apex_v8.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/RB_Golden_Apex_v8.blend')
print('APEX_V8_GEOMETRY_REPAIR '+json.dumps(changed))
