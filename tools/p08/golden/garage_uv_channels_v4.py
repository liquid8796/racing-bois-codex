"""Keep UV0 and the verified LightmapUV as exactly the first two export channels."""
import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
assert '/Garage/V3/' in bpy.data.filepath.replace('\\','/')
rows=[]
for o in bpy.data.objects['RB_Golden_Garage'].children_recursive:
    if o.type!='MESH' or '_L0_' not in o.name:continue
    m=o.data;primary=m.uv_layers[0].name
    for material in m.materials:
        if material and material.use_nodes:
            assert not any(n.type=='UVMAP' for n in material.node_tree.nodes),'Named UV channel requires explicit review'
    beforePrimary=[tuple(p.uv) for p in m.uv_layers[0].data]
    beforeLightmap=[tuple(p.uv) for p in m.uv_layers['LightmapUV'].data]
    old=[u.name for u in m.uv_layers]
    for name in old:
        if name not in (primary,'LightmapUV'):m.uv_layers.remove(m.uv_layers[name])
    assert len(m.uv_layers)==2 and m.uv_layers[1].name=='LightmapUV'
    assert beforePrimary==[tuple(p.uv) for p in m.uv_layers[0].data]
    assert beforeLightmap==[tuple(p.uv) for p in m.uv_layers[1].data]
    m.uv_layers.active_index=0;m.uv_layers[0].active_render=True
    rows.append({'name':o.name,'before':old,'after':[u.name for u in m.uv_layers],'uv0AndLightmapValuesUnchanged':True})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V4/RB_Golden_Garage.blend')
print('GARAGE_UV_CHANNELS '+json.dumps({'meshes':rows,'source':'ArtSource/P08/Golden/Garage/V4/RB_Golden_Garage.blend','visualAccepted':False}))
