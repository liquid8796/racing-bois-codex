"""Measured geometry/skin/UV/clip diagnostics for the current runtime meshes."""
import bpy,bmesh,math,json
from mathutils import Matrix
rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene
rig.animation_data_create();rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for level in range(3):
    obj=bpy.data.objects['AshV3_L'+str(level)+'_Skin']
    for key in obj.data.shape_keys.key_blocks:key.value=0
bpy.context.view_layer.update()
result={'scope':'Actual Blender geometry, skinning, UV and clip deformation diagnostics; not visual fidelity or native performance acceptance.','bones':len(rig.data.bones),'meshes':[],'clips':[],'productionAccepted':False}
for level in range(3):
    obj=bpy.data.objects['AshV3_L'+str(level)+'_Skin'];data=obj.data;data.calc_loop_triangles();uv=data.uv_layers.active
    geometric_zero=0;uv_zero=0;finite_uv=True;bad_weights=0;max_influences=0
    for triangle in data.loop_triangles:
        a,b,c=[data.vertices[i].co for i in triangle.vertices]
        if (b-a).cross(c-a).length<1e-12:geometric_zero+=1
        a,b,c=[uv.data[i].uv for i in triangle.loops]
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-12:uv_zero+=1
    for loop in uv.data:
        if not math.isfinite(loop.uv.x) or not math.isfinite(loop.uv.y):finite_uv=False
    for vertex in data.vertices:
        values=[g.weight for g in vertex.groups if obj.vertex_groups[g.group].name in rig.data.bones and g.weight>.00001]
        max_influences=max(max_influences,len(values))
        if abs(sum(values)-1)>.0001 or len(values)>4:bad_weights+=1
    bm=bmesh.new();bm.from_mesh(data)
    boundary=sum(edge.is_boundary for edge in bm.edges);nonmanifold=sum(len(edge.link_faces)>2 for edge in bm.edges)
    bm.free()
    result['meshes'].append({'name':obj.name,'vertices':len(data.vertices),'triangles':len(data.loop_triangles),'materials':[m.name for m in data.materials],
      'degenerateTriangles':geometric_zero,'degenerateUvTriangles':uv_zero,'finiteUV':finite_uv,'boundaryEdges':boundary,'nonmanifoldSharedEdges':nonmanifold,
      'badWeights':bad_weights,'maxInfluences':max_influences,'expressions':[key.name for key in data.shape_keys.key_blocks]})
depsgraph=bpy.context.evaluated_depsgraph_get();obj=bpy.data.objects['AshV3_L0_Skin']
for action in bpy.data.actions:
    if not action.name.startswith('RB_'):continue
    rig.animation_data.action=action;start,end=action.frame_range
    bounds=[];bad=0
    for fraction in [0,.25,.5,.75,1]:
        frame=start+(end-start)*fraction;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
        mesh=obj.evaluated_get(depsgraph).to_mesh()
        points=[v.co for v in mesh.vertices]
        bad+=sum(not all(math.isfinite(x) for x in p) for p in points)
        minimum=[min(p[a] for p in points) for a in range(3)];maximum=[max(p[a] for p in points) for a in range(3)]
        bounds.append({'fraction':fraction,'min':minimum,'max':maximum})
        obj.evaluated_get(depsgraph).to_mesh_clear()
    result['clips'].append({'name':action.name,'frames':[start,end],'samples':5,'nonFiniteVertices':bad,'bounds':bounds})
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
print('ASH_RUNTIME_AUDIT '+json.dumps(result))
