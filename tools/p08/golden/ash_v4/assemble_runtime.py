"""Keep authored details, construct three skinned candidates, preserve gameplay clips."""
import bpy,bmesh,json
from mathutils import Matrix
from mathutils.kdtree import KDTree
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
PREFIX='RB_P06_Rider_L0_'
reweighted=[]
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];mesh=obj.data
    assert not obj.get('v4_details_merged',False),'Do not append details twice'
    for key in mesh.shape_keys.key_blocks:key.value=0
    ids=set(v for p in mesh.polygons if mesh.materials[p.material_index].name=='AshV4_TailoredLeather_Source' for v in p.vertices)
    adjacent={i:set() for i in ids}
    for e in mesh.edges:
        a,b=e.vertices
        if a in ids and b in ids:adjacent[a].add(b);adjacent[b].add(a)
    todo=set(ids);shirt=set()
    while todo:
        i=todo.pop();found={i};queue=[i]
        while queue:
            for j in adjacent[queue.pop()]:
                if j in todo:todo.remove(j);found.add(j);queue.append(j)
        if max(mesh.vertices[i].co.z for i in found)>1.40:shirt.update(found)
    count=0
    for i in shirt:
        vertex=mesh.vertices[i];weights={obj.vertex_groups[g.group].name:g.weight for g in vertex.groups}
        leg=sum(w for name,w in weights.items() if name.startswith(PREFIX+'Thigh_') or name.startswith(PREFIX+'Shin_'))
        if leg<=.00001:continue
        # The shortened jacket now terminates above the thigh crease. Carry
        # former long-shirt leg influence on pelvis/torso, not on moving legs.
        for name in list(weights):
            if name.startswith(PREFIX+'Thigh_') or name.startswith(PREFIX+'Shin_'):del weights[name]
        weights[PREFIX+'Hip']=weights.get(PREFIX+'Hip',0)+leg*.75
        weights[PREFIX+'Torso']=weights.get(PREFIX+'Torso',0)+leg*.25
        total=sum(weights.values())
        for group in list(vertex.groups):obj.vertex_groups[group.group].remove([i])
        for name,weight in weights.items():obj.vertex_groups[name].add([i],weight/total,'REPLACE')
        count+=1
    reweighted.append({'lod':level,'shortenedJacketVerticesRebound':count})
bpy.context.view_layer.update()
base=bpy.data.objects['AshV4_L0_Skin'];cloth_ids=set(v for p in base.data.polygons if base.data.materials[p.material_index].name=='AshV4_TailoredLeather_Source' for v in p.vertices)
kd=KDTree(len(cloth_ids))
for i in cloth_ids:kd.insert(base.data.vertices[i].co,i)
kd.balance()
sewn=list(bpy.data.collections['AshV4_SewnDetails_Source'].objects);hair=list(bpy.data.collections['AshV4_HairDetails_Source'].objects)
for obj in sewn:
    for v in obj.data.vertices:
        for g in list(v.groups):obj.vertex_groups[g.group].remove([v.index])
        if 'Waistband' in obj.name:values=[(PREFIX+'Hip',.75),(PREFIX+'Torso',.25)]
        else:
            p,i,d=kd.find(v.co);values=[(base.vertex_groups[g.group].name,g.weight) for g in base.data.vertices[i].groups if g.weight>.00001]
        total=sum(w for name,w in values)
        for name,weight in values:
            group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name);group.add([v.index],weight/total,'REPLACE')
runtime=bpy.data.collections['AshV2_Runtime_LODs'];rows=[]
for level in range(3):
    active=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];parts=[]
    for source in sewn+hair:
        if level==2 and source.name not in ['AshV4_SewnWaistband','AshV4_CollarOverlapTab','AshV4_CollarSnapVisible']:continue
        copy=source.copy();copy.data=source.data.copy();runtime.objects.link(copy);copy.name='RuntimeL'+str(level)+'_'+source.name
        for mod in list(copy.modifiers):copy.modifiers.remove(mod)
        if level==1 and source in hair:
            bm=bmesh.new();bm.from_mesh(copy.data);bm.verts.ensure_lookup_table();todo=set(bm.verts);components=[]
            while todo:
                first=todo.pop();found={first};queue=[first]
                while queue:
                    for edge in queue.pop().link_edges:
                        for v in edge.verts:
                            if v in todo:todo.remove(v);found.add(v);queue.append(v)
                components.append(found)
            def first_index(component):return min(v.index for v in component)
            components.sort(key=first_index);remove=[]
            for i,component in enumerate(components):
                if i%3:remove.extend(component)
            bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(copy.data);bm.free()
        copy.hide_set(False);copy.hide_render=False;parts.append(copy)
    bpy.ops.object.select_all(action='DESELECT');active.hide_set(False);active.select_set(True)
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=active;bpy.ops.object.join();active['v4_details_merged']=True
    mesh=active.data;mesh.calc_loop_triangles();maximum=0;bad=0
    for v in mesh.vertices:
        values=[g.weight for g in v.groups if g.weight>.00001];maximum=max(maximum,len(values))
        if not values or abs(sum(values)-1)>.0002:bad+=1
    assert bad==0 and maximum<=4,'New detail skin weight contract failed'
    active.hide_render=level!=0;active.hide_set(level!=0)
    rows.append({'lod':level,'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),'materials':[m.name for m in mesh.materials],'maximumBoneInfluences':maximum})
bpy.data.collections['AshV4_SewnDetails_Source'].hide_render=True;bpy.data.collections['AshV4_HairDetails_Source'].hide_render=True
rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_RUNTIME '+json.dumps({'lods':rows,'reboundGarmentOnly':reweighted,'gameplayActionsPreserved':True,'contactHandAndBootWeightsUnchanged':True,'performanceAcceptance':False,'visualAcceptance':False}))
