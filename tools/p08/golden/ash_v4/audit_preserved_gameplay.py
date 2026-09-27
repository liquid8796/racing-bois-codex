import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
def action_values(action):
    curves=[]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    curves.append((curve.data_path,curve.array_index,curve.extrapolation,
                        [(tuple(p.co),tuple(p.handle_left),tuple(p.handle_right),p.interpolation,p.handle_left_type,p.handle_right_type) for p in curve.keyframe_points]))
    return curves
def capture(version):
    rig=bpy.data.objects['RB_P06_Rider_Rig']
    bones=[(b.name,b.parent.name if b.parent else '',[tuple(row) for row in b.matrix_local],tuple(b.head_local),tuple(b.tail_local)) for b in rig.data.bones]
    actions={a.name:action_values(a) for a in bpy.data.actions if a.name.startswith('RB_') and a.name!='RB_MenuHero'}
    contacts=[]
    for level in range(3):
        obj=bpy.data.objects['AshV'+str(version)+'_L'+str(level)+'_Skin'];m=obj.data
        roles={i:set() for i in range(len(m.vertices))}
        for p in m.polygons:
            for i in p.vertices:roles[i].add(m.materials[p.material_index].name)
        values=[]
        for v in m.vertices:
            weights=sorted((obj.vertex_groups[g.group].name,g.weight) for g in v.groups)
            glove=any(('Finger_' in n or 'Hand_' in n) and w>.2 for n,w in weights) and any('CharcoalLeather' in r or 'LeatherDetails' in r for r in roles[v.index])
            boot=v.co.z<.32 and any('BootLeather' in r or 'Rubber' in r for r in roles[v.index])
            if glove or boot:values.append((v.index,tuple(v.co),weights))
        contacts.append(values)
    return {'bones':bones,'actions':actions,'contacts':contacts}
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V3/RB_Golden_Ash_V3.blend',load_ui=False,use_scripts=False)
before=capture(3)
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',load_ui=False,use_scripts=False)
after=capture(4)
assert before['bones']==after['bones'],'Rig rest changed'
assert before['actions']==after['actions'],'Gameplay animation values changed'
assert before['contacts']==after['contacts'],'Original glove/boot contact geometry or weights changed'
print('ASH_V4_PRESERVATION '+json.dumps({'passed':True,'bonesExact':len(before['bones']),'gameplayActionsExact':len(before['actions']),
    'actionCurvesCompared':sum(len(v) for v in before['actions'].values()),'contactVerticesExactByLod':[len(v) for v in before['contacts']],
    'preservesPositionsWeightsAndIndicesForContactSurfaces':True,'newMenuAction':'RB_MenuHero','visualAcceptance':False}))
