import bpy,json
ROOT='D:/Project/Unity/racing-bois/'

def capture():
    rows={}
    for o in bpy.data.objects['RB_Golden_Garage'].children_recursive:
        if o.type!='MESH':continue
        m=o.data;m.calc_loop_triangles()
        rows[o.name]={'vertices':[tuple(v.co) for v in m.vertices],
            'triangles':[tuple(t.vertices) for t in m.loop_triangles],
            'normals':[tuple(n.vector) for n in m.corner_normals],
            'matrix':[tuple(v) for v in o.matrix_world],
            'materials':[a.name for a in m.materials],'indices':[p.material_index for p in m.polygons],
            'lightmap':[tuple(v.uv) for v in m.uv_layers['LightmapUV'].data] if m.uv_layers.get('LightmapUV') else None}
    return rows

bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V4/RB_Golden_Garage.blend',load_ui=False,use_scripts=False)
baseline=capture()
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage.blend',load_ui=False,use_scripts=False)
candidate=capture()
assert baseline==candidate,'A non-primary-UV geometry/material-index/lightmap value changed'
floor=bpy.data.materials['Garage_Floor'];principled=next(n for n in floor.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
assert principled.inputs['Coat Weight'].default_value==0
normal=next(n for n in floor.node_tree.nodes if n.type=='NORMAL_MAP')
assert abs(normal.inputs['Strength'].default_value-.55)<1e-6
print('GARAGE_V5_PRESERVATION '+json.dumps({'passed':True,'meshCount':len(candidate),'verticesTriangleIndicesCornerNormalsTransformsMaterialSlotsAndAssignmentsExact':True,'lod0LightmapUvExact':True,'originalFloorNormal':normal.inputs['Strength'].default_value,'defaultCoatWeight':0,'visualAccepted':False}))
