"""Build inspectable skinned LODs from evaluated source, preserving authoring parts.

All geometry, UV cleanup and skinning operations happen through direct Blender
MCP. This is technical preparation, not concept-fidelity acceptance.
"""
import bpy,bmesh,math,json
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];root=bpy.data.objects['RB_Golden_Ash_V2'];PREFIX='RB_P06_Rider_L0_'
rig.animation_data_create();rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
body=bpy.data.objects['AshV2_Body']
for key in body.data.shape_keys.key_blocks:key.value=0
bpy.context.view_layer.update();depsgraph=bpy.context.evaluated_depsgraph_get()
parts=[obj for obj in rig.children if obj.type=='MESH']
source_collection=bpy.data.collections.get('AshV2_Editable_Source')
if source_collection is None:
    source_collection=bpy.data.collections.new('AshV2_Editable_Source');scene.collection.children.link(source_collection)
source_collection.hide_viewport=False;bpy.context.view_layer.update()
export_collection=bpy.data.collections.get('AshV2_Runtime_LODs')
if export_collection is None:
    export_collection=bpy.data.collections.new('AshV2_Runtime_LODs');scene.collection.children.link(export_collection)
def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
def clear_modifiers(obj):
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
def fix_uv(mesh):
    if not mesh.uv_layers:mesh.uv_layers.new(name='UV0')
    uv=mesh.uv_layers.active
    for polygon in mesh.polygons:
        points=[uv.data[i].uv.copy() for i in polygon.loop_indices]
        # Repair the zero-to-one wrap on periodic manufactured surfaces.
        if points and max(p.x for p in points)-min(p.x for p in points)>.75:
            for i in polygon.loop_indices:
                if uv.data[i].uv.x<.125:uv.data[i].uv.x+=1
        area=abs(sum(points[i].x*points[(i+1)%len(points)].y-points[(i+1)%len(points)].x*points[i].y for i in range(len(points))))*.5
        if area<1e-12:
            dominant=0
            for axis in [1,2]:
                if abs(polygon.normal[axis])>abs(polygon.normal[dominant]):dominant=axis
            axes=[axis for axis in range(3) if axis!=dominant]
            values=[mesh.vertices[mesh.loops[i].vertex_index].co for i in polygon.loop_indices]
            lows=[min(p[a] for p in values) for a in axes];spans=[max(p[a] for p in values)-low for a,low in zip(axes,lows)]
            for i in polygon.loop_indices:
                p=mesh.vertices[mesh.loops[i].vertex_index].co
                uv.data[i].uv=(.81+.12*(p[axes[0]]-lows[0])/max(spans[0],1e-6),.81+.12*(p[axes[1]]-lows[1])/max(spans[1],1e-6))
def cleanup(mesh,preserve_vertices,allow_open):
    mesh.calc_loop_triangles()
    degenerate=False
    for triangle in mesh.loop_triangles:
        a,b,c=[mesh.vertices[i].co for i in triangle.vertices]
        if (b-a).cross(c-a).length<1e-12:degenerate=True
    bm=bmesh.new();bm.from_mesh(mesh)
    closed_manifold=all(len(edge.link_faces)==2 for edge in bm.edges)
    if not preserve_vertices and (not closed_manifold or degenerate):
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
        bm.verts.ensure_lookup_table();bm.verts.index_update();face_sets={};duplicates=[]
        for face in bm.faces:
            key=tuple(sorted(v.index for v in face.verts))
            if key in face_sets:duplicates.extend([face_sets[key],face])
            else:face_sets[key]=face
        if duplicates:bmesh.ops.delete(bm,geom=list(set(duplicates)),context='FACES_ONLY')
    if not allow_open:
        boundary=[edge for edge in bm.edges if edge.is_boundary]
        if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update();fix_uv(mesh)
copies=[]
for source in parts:
    expression_coords={}
    evaluated=source.evaluated_get(depsgraph)
    neutral=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=depsgraph)
    if source==body:
        for name in ['Happy','Focused']:
            source.data.shape_keys.key_blocks[name].value=1;bpy.context.view_layer.update()
            expression=bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph),preserve_all_data_layers=True,depsgraph=depsgraph)
            if len(expression.vertices)!=len(neutral.vertices):raise RuntimeError('Expression topology changed')
            expression_coords[name]=[v.co.copy() for v in expression.vertices]
            bpy.data.meshes.remove(expression);source.data.shape_keys.key_blocks[name].value=0;bpy.context.view_layer.update()
    copy=source.copy();copy.data=neutral;export_collection.objects.link(copy);clear_modifiers(copy);copy.name='Export_'+source.name
    # Blender joins UV layers by NAME. Normalize before joining, otherwise
    # generated UV0 parts and imported UVMap parts land in different channels.
    if not copy.data.uv_layers:copy.data.uv_layers.new(name='UV0')
    copy.data.uv_layers.active.name='UV0'
    copy.data.uv_layers.active.active_render=True
    # The copied group table matches evaluated deform layers; only actual rig
    # groups are retained, excluding the authoring mask selection.
    for group in list(copy.vertex_groups):
        if group.name not in rig.data.bones:copy.vertex_groups.remove(group)
    before=len(copy.data.vertices)
    allow_open=source.name in ['AshV2_Hair','AshV2_Brows']
    cleanup(copy.data,source==body,allow_open)
    if source==body:
        if len(copy.data.vertices)!=before:raise RuntimeError('Body expression index mapping changed')
        copy.shape_key_add(name='Basis',from_mix=False)
        for name,coords in expression_coords.items():
            key=copy.shape_key_add(name=name,from_mix=False);key.value=0
            for vertex,position in zip(key.data,coords):vertex.co=position
    copies.append(copy)
    for collection in list(source.users_collection):collection.objects.unlink(source)
    source_collection.objects.link(source)
source_collection.hide_render=True;source_collection.hide_viewport=True
body_copy=next(obj for obj in copies if obj.name=='Export_AshV2_Body')
bpy.ops.object.select_all(action='DESELECT')
for obj in copies:obj.select_set(True)
bpy.context.view_layer.objects.active=body_copy;bpy.ops.object.join()
lod0=bpy.context.object;lod0.name='AshV2_L0_Skin';lod0.parent=rig
bpy.ops.object.material_slot_remove_unused()
valid_bones=set(rig.data.bones.keys())
def normalize(obj):
    maximum=0
    for vertex in obj.data.vertices:
        values=[(g.group,g.weight) for g in vertex.groups if obj.vertex_groups[g.group].name in valid_bones and g.weight>.00001]
        values.sort(key=weight_sort,reverse=True);values=values[:4];total=sum(w for i,w in values)
        if total<=0:raise RuntimeError('Unweighted export vertex '+obj.name+' '+str(vertex.index))
        previous=[g.group for g in vertex.groups]
        for index in previous:obj.vertex_groups[index].remove([vertex.index])
        for index,weight in values:obj.vertex_groups[index].add([vertex.index],weight/total,'REPLACE')
        maximum=max(maximum,len(values))
    return maximum
def weight_sort(pair):return pair[1]
normalize(lod0)
kd=KDTree(len(lod0.data.vertices))
for vertex in lod0.data.vertices:kd.insert(vertex.co,vertex.index)
kd.balance()
expression_deltas={}
for name in ['Happy','Focused']:
    key=lod0.data.shape_keys.key_blocks[name]
    expression_deltas[name]=[key.data[i].co-v.co for i,v in enumerate(lod0.data.vertices)]
for level,ratio in [(1,.52),(2,.22)]:
    obj=lod0.copy();obj.data=lod0.data.copy();export_collection.objects.link(obj);obj.name='AshV2_L'+str(level)+'_Skin';obj.shape_key_clear();active(obj)
    modifier=obj.modifiers.new('Silhouette LOD reduction','DECIMATE');modifier.ratio=ratio;modifier.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=modifier.name);normalize(obj);fix_uv(obj.data)
    obj.shape_key_add(name='Basis',from_mix=False)
    for name in ['Happy','Focused']:
        key=obj.shape_key_add(name=name,from_mix=False);key.value=0
        for vertex in obj.data.vertices:
            neighbours=kd.find_n(vertex.co,3);total=0;delta=Vector()
            for position,index,distance in neighbours:
                weight=1/max(distance,.00001)**2;total+=weight;delta+=expression_deltas[name][index]*weight
            key.data[vertex.index].co+=delta/total
    obj.hide_render=True
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin'];modifier=obj.modifiers.new('Anatomical skin deformation','ARMATURE');modifier.object=rig;modifier.use_deform_preserve_volume=False
for name,position in [('Forward',(0,-1,0)),('Ground_L',(.155,0,0)),('Ground_R',(-.155,0,0))]:
    marker=bpy.data.objects.new(name,None);scene.collection.objects.link(marker);marker.parent=root;marker.location=position
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
counts=[]
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin'];obj.data.calc_loop_triangles()
    counts.append({'level':level,'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles),'materials':[m.name for m in obj.data.materials]})
print('ASH_LODS '+json.dumps({'lods':counts,'bones':len(rig.data.bones),'productionAccepted':False}))
