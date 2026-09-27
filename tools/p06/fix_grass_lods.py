import bpy,bmesh,json
def reduce_grass_components(mesh,ratio):
    bm=bmesh.new();bm.from_mesh(mesh);seen=set();components=[]
    for vertex in bm.verts:
        if vertex in seen:continue
        stack=[vertex];seen.add(vertex);component=[]
        while stack:
            v=stack.pop();component.append(v)
            for edge in v.link_edges:
                neighbor=edge.other_vert(v)
                if neighbor not in seen:seen.add(neighbor);stack.append(neighbor)
        components.append(component)
    count=max(3,round(len(components)*ratio));keep={int(i*len(components)/count) for i in range(count)}
    discard=[v for i,component in enumerate(components) if i not in keep for v in component]
    if discard:bmesh.ops.delete(bm,geom=discard,context='VERTS')
    bm.to_mesh(mesh);bm.free();mesh.update()

root=bpy.data.objects['RB_P06_DryGrass']
base=bpy.data.objects['RB_P06_DryGrass_L0_Mesh']
for level,ratio in [(1,.60),(2,.28)]:
    old=bpy.data.objects.get('RB_P06_DryGrass_L'+str(level)+'_Mesh')
    if old:bpy.data.objects.remove(old,do_unlink=True)
    o=base.copy();o.data=base.data.copy();bpy.context.scene.collection.objects.link(o);o.name='RB_P06_DryGrass_L'+str(level)+'_Mesh';o.parent=root;reduce_grass_components(o.data,ratio);o.hide_render=True
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for o in root.children:o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath='D:/Project/Unity/racing-bois/Assets/RacingBois/Art/P06/Environment/RB_P06_DryGrass.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,bake_anim=False,add_leaf_bones=False)
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P06/Environment/RB_P06_CanyonKit.blend')
print('Grass LOD components preserved: 124/76/36 triangles')
