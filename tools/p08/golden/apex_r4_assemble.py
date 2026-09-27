"""Build staged R4 LOD meshes after multiview review; not visual approval."""
import bpy,bmesh,json,math
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/';NAME='RB_Golden_Apex_r4';root=bpy.data.objects[NAME];scene=bpy.context.scene
assert not any(o.name.startswith('Apex_L0_') for o in root.children_recursive), 'Reload R4 editable before assembly'

def coord(p):return Vector((p[0],p[2],p[1]))
def marker(name,p):
    o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.parent=root;o.location=coord(p)
for name,p in {'Forward':(0,0,1.1),'Semantic_Left':(-.5,0,0),'Semantic_Right':(.5,0,0),'Ground_Front':(0,0,.715),'Ground_Rear':(0,0,-.715),'Contact_Seat':(0,.824,-.37),'Contact_Grip_L':(-.294,.927,.389),'Contact_Grip_R':(.294,.927,.389),'Contact_Foot_L':(-.286,.342,-.249),'Contact_Foot_R':(.286,.342,-.249)}.items():marker(name,p)
groups={'Body':[],'Front':[],'Rear':[]}
for o in root.children_recursive:
    if o.type=='MESH':
        assert o.get('asset_group') in groups,o.name
        # Blender joins UV layers by name. Preserve each component's active
        # authored field instead of creating parallel blank layers on join.
        active=o.data.uv_layers.active
        assert active is not None,'Missing authored UVs: '+o.name
        for layer in list(o.data.uv_layers):
            if layer!=active:o.data.uv_layers.remove(layer)
        active.name='UV0_SurfaceMetres'
        groups[o.get('asset_group')].append(o)

assembled=[]
for group,objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name='Apex_L0_'+group
    pivot=(0,0,0) if group=='Body' else (0,.315,.715 if group=='Front' else -.715)
    scene.cursor.location=coord(pivot);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    matrix=o.matrix_world.copy();o.parent=root if group=='Body' else bpy.data.objects[NAME+'_Wheel_'+group];o.matrix_world=matrix
    assembled.append(o)
def remove_collapsed_lod_fragments(o):
    # Only tiny disconnected open LOD fragments may disappear. Main skins
    # must stay manifold; a bad main component is a hard failure.
    bm=bmesh.new();bm.from_mesh(o.data);seen=set();remove=set();drop_faces=set()
    for seed in bm.verts:
        if seed in seen:continue
        component=set();todo=[seed]
        while todo:
            vertex=todo.pop()
            if vertex in component:continue
            component.add(vertex);seen.add(vertex)
            for edge in vertex.link_edges:todo.append(edge.other_vert(vertex))
        edges={edge for vertex in component for edge in vertex.link_edges}
        faces={face for vertex in component for face in vertex.link_faces}
        if not faces:
            remove.update(component);continue
        if not any(not edge.is_manifold for edge in edges):continue
        first=next(iter(component));end=first
        for vertex in component:
            if (vertex.co-first.co).length_squared>(end.co-first.co).length_squared:end=vertex
        start=end
        for vertex in component:
            if (vertex.co-end.co).length_squared>(start.co-end.co).length_squared:start=vertex
        axis=(end.co-start.co).normalized()
        radius=max((vertex.co-start.co).cross(axis).length for vertex in component)
        assert len(faces)<=6 and radius<.009 and sum(face.calc_area() for face in faces)<.003,'Broken nontrivial LOD surface: '+o.name
        remove.update(component);drop_faces.update(faces)
    assert len(drop_faces)<len(bm.faces)*.10,'LOD cleanup would remove excessive geometry'
    count=len(remove)
    if remove:bmesh.ops.delete(bm,geom=list(remove),context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
    assert len(o.data.polygons)>0,'LOD cleanup produced empty geometry'
    return count

for original in assembled:
    for level,ratio in [(1,.50),(2,.20)]:
        o=original.copy();o.data=original.data.copy();scene.collection.objects.link(o);o.name=original.name.replace('_L0_','_L%d_'%level)
        bpy.context.view_layer.objects.active=o;modifier=o.modifiers.new('Silhouette preserving LOD','DECIMATE');modifier.ratio=ratio;modifier.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=modifier.name)
        o.hide_render=True
report=[];failure_count=0
for o in root.children_recursive:
    if o.type!='MESH':continue
    bpy.context.view_layer.objects.active=o;modifier=o.modifiers.new('Explicit export triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=modifier.name)
    o.data.validate(clean_customdata=False);o.data.update()
    collapsed_vertices=remove_collapsed_lod_fragments(o) if '_L2_' in o.name else 0
    o.data.calc_loop_triangles();bad=0
    for tri in o.data.loop_triangles:
        a,b,c=[o.data.vertices[i].co for i in tri.vertices]
        bad+=(o.matrix_world.to_3x3()@(b-a)).cross(o.matrix_world.to_3x3()@(c-a)).length_squared<=1e-16
    uv=o.data.uv_layers.active;fixed=0
    for face in o.data.polygons:
        p=[uv.data[i].uv.copy() for i in face.loop_indices]
        area=abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))
        if area<2e-12:
            axis=0 if abs(face.normal.x)>=max(abs(face.normal.y),abs(face.normal.z)) else 1 if abs(face.normal.y)>=abs(face.normal.z) else 2;axes=[i for i in range(3) if i!=axis]
            origin=o.data.vertices[o.data.loops[face.loop_start].vertex_index].co.copy()
            for loop in face.loop_indices:
                p=o.data.vertices[o.data.loops[loop].vertex_index].co-origin;uv.data[loop].uv=(p[axes[0]]*2,p[axes[1]]*2)
            fixed+=1
    bm=bmesh.new();bm.from_mesh(o.data);topology_failures=sum(not e.is_manifold for e in bm.edges);bm.free()
    failure_count+=bad+topology_failures;report.append({'name':o.name,'triangles':len(o.data.loop_triangles),'physicalFailures':bad,'nonManifoldEdges':topology_failures,'repairedPlanarCapUvs':fixed,'removedCollapsedLodVertices':collapsed_vertices})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_assembled.blend')
print('APEX_R4_ASSEMBLED '+json.dumps({'objects':report,'physicalFailures':sum(r['physicalFailures'] for r in report),'nonManifoldEdges':sum(r['nonManifoldEdges'] for r in report),'structuralFailures':failure_count,'visualAccepted':False,'exported':False}))
assert failure_count==0,'Fix source/LOD topology before export; do not weaken the physical gate'
