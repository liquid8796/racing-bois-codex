"""Rename only traffic orientation markers in saved sources via real Blender MCP."""
import bpy,json

ROOT='D:/Project/Unity/racing-bois/'
reports=[]
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'_local/p06-before-traffic-marker-fix.blend')
for name in ['RB_P06_TrafficCoupe','RB_P06_TrafficVan']:
    bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P06/Hero/'+name+'.blend',load_ui=False,use_scripts=False)
    root=bpy.data.objects[name]
    meshes=[obj for obj in root.children_recursive if obj.type=='MESH']
    before=[([tuple(v.co) for v in obj.data.vertices],
             [tuple(poly.vertices) for poly in obj.data.polygons],
             [tuple(uv.uv) for uv in obj.data.uv_layers.active.data]) for obj in meshes]
    changed=[]
    for suffix in ['FrontMarker','RearMarker']:
        matches=[obj for obj in root.children_recursive
                 if obj.type=='EMPTY' and (obj.name==suffix or obj.name.startswith(suffix+'.') or obj.name==name+'_'+suffix)]
        if len(matches)!=1:raise RuntimeError('Ambiguous traffic marker '+name+' '+suffix)
        obj=matches[0];previous=obj.name;obj.name=name+'_'+suffix
        changed.append({'before':previous,'after':obj.name,'localPositionBlenderMeters':list(obj.location)})
    after=[([tuple(v.co) for v in obj.data.vertices],
            [tuple(poly.vertices) for poly in obj.data.polygons],
            [tuple(uv.uv) for uv in obj.data.uv_layers.active.data]) for obj in meshes]
    if before!=after:raise RuntimeError('Marker-only operation changed geometry or UV')
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for obj in root.children_recursive:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    # Opening a .blend inside an MCP timer invalidates the implicit editor
    # selection context; bind the exact export set explicitly.
    selected=[root]+list(root.children_recursive)
    with bpy.context.temp_override(selected_objects=selected,selected_editable_objects=selected,active_object=root):
        bpy.ops.export_scene.fbx(filepath=ROOT+'Assets/RacingBois/Art/P06/Hero/'+name+'.fbx',use_selection=True,
            object_types={'MESH','EMPTY','ARMATURE'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,
            bake_anim=False,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
            bake_anim_simplify_factor=0,path_mode='AUTO')
    bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P06/Hero/'+name+'.blend')
    reports.append({'name':name,'markers':changed,'geometryAndUvUnchanged':before==after})
print(json.dumps({'passed':True,'assets':reports,'scope':'Marker names only; source geometry, UV, collider target and render appearance unchanged.'}))
