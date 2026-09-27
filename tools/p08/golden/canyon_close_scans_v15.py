"""Close real scan boundaries and orient closed shells outward; no material culling workaround."""
import bpy,bmesh,json,math
from mathutils import Vector
from mathutils.kdtree import KDTree
ROOT='D:/Project/Unity/racing-bois/'
root=bpy.data.objects['RB_Golden_Canyon']
material=bpy.data.materials['Canyon_Sandstone']
records=[]
for obj in root.children_recursive:
    if obj.type!='MESH' or not any(m.name in ['Canyon_Cliff01','Canyon_Cliff02','Canyon_Cliff03'] for m in obj.data.materials):continue
    assert obj.matrix_world.determinant()>0,'Unexpected mirrored placement '+obj.name
    if material not in list(obj.data.materials):obj.data.materials.append(material)
    cap_slot=list(obj.data.materials).index(material)
    bm=bmesh.new();bm.from_mesh(obj.data)
    boundary_before=sum(1 for edge in bm.edges if edge.is_boundary)
    uv=bm.loops.layers.uv.active
    assert uv is not None,'Missing scan UV '+obj.name
    added=0
    if boundary_before:
        bm.free()
        original_points=[vertex.co.copy() for vertex in obj.data.vertices]
        tree=KDTree(len(original_points))
        for index,point in enumerate(original_points):tree.insert(point,index)
        tree.balance()
        bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
        shell=obj.modifiers.new('Closed geological backing','SOLIDIFY')
        thickness=max(.03,min(.35,min(obj.dimensions)*.03))
        shell.solidify_mode='EXTRUDE';shell.thickness=thickness;shell.offset=0;shell.use_rim=True;shell.use_even_offset=False
        shell.material_offset=1;shell.material_offset_rim=1
        bpy.ops.object.modifier_apply(modifier=shell.name)
        maximum_displacement=max(tree.find(vertex.co)[2] for vertex in obj.data.vertices)
        assert maximum_displacement<=thickness*.51+.0001,'Unbounded backing displacement '+obj.name
        bm=bmesh.new();bm.from_mesh(obj.data);uv=bm.loops.layers.uv.active
        for face in bm.faces:
            if face.material_index!=cap_slot:continue
            added+=1;face.normal_update();normal=face.normal
            axis=0 if abs(normal.x)>abs(normal.y) and abs(normal.x)>abs(normal.z) else 1 if abs(normal.y)>abs(normal.z) else 2
            for loop in face.loops:
                point=obj.matrix_world@loop.vert.co
                loop[uv].uv=(point.y/2.4,point.z/2.4) if axis==0 else (point.x/2.4,point.z/2.4) if axis==1 else (point.x/2.4,point.y/2.4)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bmesh.ops.dissolve_degenerate(bm,dist=.00001,edges=list(bm.edges))
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
    assert all(edge.is_manifold for edge in bm.edges),'Boundary/nonmanifold edge remains '+obj.name
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    remaining=set(bm.faces);volumes=[];flipped=0
    while remaining:
        seed=remaining.pop();component=[seed];stack=[seed]
        while stack:
            face=stack.pop()
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in remaining:remaining.remove(linked);component.append(linked);stack.append(linked)
        volume=0.0
        for face in component:
            a,b,c=[vertex.co for vertex in face.verts]
            volume+=a.dot(b.cross(c))/6.0
        assert abs(volume)>1e-10,'Zero-volume closed component '+obj.name
        if volume<0:
            for face in component:face.normal_flip()
            flipped+=len(component)
        volumes.append(abs(volume))
    bm.to_mesh(obj.data);bm.free();obj.data.update();obj.data.calc_loop_triangles()
    minimum=float('inf')
    for tri in obj.data.loop_triangles:
        a,b,c=[obj.data.vertices[i].co for i in tri.vertices]
        minimum=min(minimum,(b-a).cross(c-a).length_squared)
    assert minimum>1e-16,'Physical triangle threshold fails '+obj.name
    records.append({'name':obj.name,'boundaryEdgesBefore':boundary_before,'boundaryEdgesAfter':0,'capsAdded':added,'closedComponentCount':len(volumes),'positiveComponentVolumes':volumes,'facesFlipped':flipped,'minimumCrossSquared':minimum,'triangles':len(obj.data.loop_triangles)})

bpy.ops.object.select_all(action='DESELECT')
for obj in root.children_recursive:obj.hide_set(False);obj.select_set(True)
root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=ROOT+'_local/p08-canyon-v15-staging/RB_Golden_Canyon.fbx',use_selection=True,object_types={'EMPTY','MESH'},axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=True)
for obj in root.children_recursive:
    if '_L1_' in obj.name or '_L2_' in obj.name:obj.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Canyon/V15/RB_Golden_Canyon.blend')
print('CANYON_CLOSED_SCANS '+json.dumps({'passed':True,'materialCullOffApplied':False,'objects':records}))
