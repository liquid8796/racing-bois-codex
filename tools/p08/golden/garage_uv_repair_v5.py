"""Recover joined primary UVs from V3, keep V4 geometry/normals/lightmap values exact.
Run through the direct task-owned Blender MCP 9877. No libraries/append/scripts.
"""
import bpy,json,math
ROOT='D:/Project/Unity/racing-bois/'
V3=ROOT+'ArtSource/P08/Golden/Garage/V3/RB_Golden_Garage.blend'
V4=ROOT+'ArtSource/P08/Golden/Garage/V4/RB_Golden_Garage.blend'
V5=ROOT+'ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage.blend'
assert bpy.data.filepath.replace('\\','/').endswith('/Garage/V4/RB_Golden_Garage.blend')

def geometry(mesh):
    return {'vertices':[tuple(v.co) for v in mesh.vertices],
        'faces':[tuple(p.vertices) for p in mesh.polygons],
        'corners':[loop.vertex_index for loop in mesh.loops],
        'normals':[tuple(n.vector) for n in mesh.corner_normals],
        'smooth':[p.use_smooth for p in mesh.polygons],
        'materialIndices':[p.material_index for p in mesh.polygons]}

def face_area(points):
    origin=points[0]
    return abs(sum((points[i][0]-origin[0])*(points[(i+1)%len(points)][1]-origin[1])-
        (points[(i+1)%len(points)][0]-origin[0])*(points[i][1]-origin[1]) for i in range(len(points)))*.5)

def values(layer):return [tuple(p.uv) for p in layer.data]

bpy.ops.wm.open_mainfile(filepath=V3,load_ui=False,use_scripts=False)
reference={}
for o in bpy.data.objects:
    if o.type=='MESH' and o.name.startswith('Garage_L'):
        reference[o.name]={'geometry':geometry(o.data),'layers':{l.name:values(l) for l in o.data.uv_layers if l.name!='LightmapUV'}}
bpy.ops.wm.open_mainfile(filepath=V4,load_ui=False,use_scripts=False)
rows=[]
for o in bpy.data.objects:
    if o.type!='MESH' or not o.name.startswith('Garage_L'):continue
    mesh=o.data; before=geometry(mesh); matrix=[tuple(row) for row in o.matrix_world]
    assert reference[o.name]['geometry']==before, 'V3/V4 topology or normals changed: '+o.name
    lightmap=values(mesh.uv_layers['LightmapUV']) if mesh.uv_layers.get('LightmapUV') else None
    primary=mesh.uv_layers[0]; prior_primary=values(primary)
    merged=0; projected=0; bad_before=0; after_bad=0; replaced_materials={}
    for poly in mesh.polygons:
        points=[tuple(primary.data[i].uv) for i in poly.loop_indices]
        if face_area(points)>1e-14 or poly.area<=1e-12:continue
        bad_before+=1; chosen=None; best=1e-14
        for name,layer in reference[o.name]['layers'].items():
            candidate=[layer[i] for i in poly.loop_indices]; area=face_area(candidate)
            if area>best:chosen=candidate;best=area
        material=mesh.materials[poly.material_index].name
        if chosen is not None:
            for i,p in zip(poly.loop_indices,chosen):primary.data[i].uv=p
            merged+=1
        else:
            # Original recipe projected world positions onto axes chosen using a
            # local normal, collapsing some rotated cylinder faces. Keep metric
            # scale but choose axes from the actual transformed face normal.
            normal=o.matrix_world.to_3x3().inverted().transposed()@poly.normal
            if abs(normal.x)>=max(abs(normal.y),abs(normal.z)):axes=(1,2)
            elif abs(normal.y)>=abs(normal.z):axes=(0,2)
            else:axes=(0,1)
            tile=2.0 if material=='Garage_Floor' else 2.2 if material in ['Garage_Concrete','Garage_NearConcrete'] else 1.0
            for i in poly.loop_indices:
                point=o.matrix_world@mesh.vertices[mesh.loops[i].vertex_index].co
                primary.data[i].uv=(point[axes[0]]/tile,point[axes[1]]/tile)
            projected+=1
        replaced_materials[material]=replaced_materials.get(material,0)+1
    # UV0 is a deliberately repeating metric projection, not an exclusive
    # texture atlas. Only LightmapUV is required to pack uniquely in0..1.
    original_layers=[l.name for l in mesh.uv_layers]
    primary_name=primary.name
    for name in original_layers:
        if name not in [primary_name,'LightmapUV']:mesh.uv_layers.remove(mesh.uv_layers[name])
    mesh.uv_layers[0].name='UV0_MetricTile'; mesh.uv_layers.active_index=0; mesh.uv_layers[0].active_render=True
    primary=mesh.uv_layers[0]
    for poly in mesh.polygons:
        if poly.area>1e-12 and face_area([tuple(primary.data[i].uv) for i in poly.loop_indices])<=1e-14:after_bad+=1
    assert after_bad==0,'Unrepaired primary UV face: '+o.name
    assert geometry(mesh)==before, 'Geometry/normals modified: '+o.name
    assert [tuple(row) for row in o.matrix_world]==matrix
    if lightmap is not None:
        assert len(mesh.uv_layers)==2 and mesh.uv_layers[1].name=='LightmapUV'
        assert values(mesh.uv_layers[1])==lightmap
    else:assert len(mesh.uv_layers)==1
    changed_loops=sum(a!=tuple(b.uv) for a,b in zip(prior_primary,primary.data))
    rows.append({'name':o.name,'originalLayers':original_layers,'layers':[l.name for l in mesh.uv_layers],
        'collapsedFacesBefore':bad_before,'mergedAlternateFaces':merged,'worldMetricProjectedFaces':projected,
        'collapsedFacesAfter':after_bad,'changedLoops':changed_loops,'materialsChanged':replaced_materials,
        'geometryNormalsAndTransformExact':True,'verifiedLightmapExact':lightmap is not None,
        'intentionalPrimaryMetricTiling':True,'vertices':len(mesh.vertices),'polygons':len(mesh.polygons)})
for material in bpy.data.materials:
    if material.use_nodes:
        assert not any(n.type=='UVMAP' for n in material.node_tree.nodes),'Named UV map binding needs explicit review'
bpy.context.scene.render.filepath=ROOT+'docs/p08/golden/garage/v5/uv-repaired-no-coat.png'
bpy.context.scene.render.resolution_x=1672;bpy.context.scene.render.resolution_y=941;bpy.context.scene.render.resolution_percentage=100
bpy.context.scene.cycles.samples=48
bpy.ops.wm.save_as_mainfile(filepath=V5)
print('GARAGE_V5_REPAIR '+json.dumps({'source':V5,'objects':rows,'meshCount':len(rows),
    'sourceV3Preserved':True,'sourceV4Preserved':True,'geometryModified':False,'visualAccepted':False}))
