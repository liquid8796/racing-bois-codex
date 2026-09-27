import bpy,math,json
ROOT='D:/Project/Unity/racing-bois/';counts=[]
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];m=obj.data
    assert not obj.get('v4_chin_strap_fit',False)
    ids=set(i for p in m.polygons if m.materials[p.material_index].name in ['AshV3_BootLeather_Baked','AshV2_AgedBrass_Baked'] for i in p.vertices)
    changed=0
    for i in ids:
        p=m.vertices[i].co.copy()
        if 1.536<p.z<1.618 and p.y<-.035 and abs(p.x)<.102:
            lift=.028*max(0,1-(abs(p.x)/.110)**2)
            saved=[k.data[i].co.copy() for k in m.shape_keys.key_blocks];p.z+=lift;m.vertices[i].co=p
            for key,co in zip(m.shape_keys.key_blocks,saved):co.z+=lift;key.data[i].co=co
            m.attributes['AshV4_RestMeters'].data[i].vector=p;changed+=1
    m.update();obj['v4_chin_strap_fit']=True;counts.append({'lod':level,'changedVertices':changed})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_CHIN_STRAP '+json.dumps(counts))
