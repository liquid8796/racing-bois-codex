import bpy,math,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
root=bpy.data.objects['RB_Golden_Garage'];baseline={}
for o in root.children_recursive:
    if o.type!='MESH':continue
    m=o.data;m.calc_loop_triangles();normal_matrix=o.matrix_world.to_3x3().inverted().transposed()
    rows=[]
    for tri in m.loop_triangles:
        rows.append({'positions':[tuple(o.matrix_world@m.vertices[v].co) for v in tri.vertices],
            'uvs':[[tuple(layer.data[loop].uv) for loop in tri.loops] for layer in m.uv_layers],
            'normals':[tuple((normal_matrix@m.corner_normals[loop].vector).normalized()) for loop in tri.loops],
            'material':m.materials[m.polygons[tri.polygon_index].material_index].name})
    baseline[o.name]={'triangles':rows,'layers':[u.name for u in m.uv_layers]}
original_names={o:o.name for o in [root]+list(root.children_recursive)}
before=set(bpy.data.objects);meshes_before=set(bpy.data.meshes);created=[];reports=[]
try:
    for o,name in original_names.items():o.name='SourceV7_'+name
    bpy.ops.import_scene.fbx(filepath=ROOT+'_local/p08-garage-v7-staging/RB_Golden_Garage.fbx',use_anim=False,use_image_search=False)
    created=list(set(bpy.data.objects)-before);imported=[o for o in created if o.type=='MESH']
    assert {o.name for o in imported}==set(baseline),'Renderer coverage changed'
    for o in imported:
        m=o.data;m.calc_loop_triangles();expected=baseline[o.name];source=expected['triangles']
        assert len(m.loop_triangles)==len(source),o.name
        assert [u.name for u in m.uv_layers]==expected['layers'],o.name
        normal_matrix=o.matrix_world.to_3x3().inverted().transposed()
        position_error=0;normal_angle=0;uv_error=0;uv_exact=True;material_mismatch=0;order_bad=0;physical_bad=0
        uv_bad={name:0 for name in expected['layers']};uv_min={name:1 for name in expected['layers']}
        for index,tri in enumerate(m.loop_triangles):
            wanted=source[index];positions=[o.matrix_world@m.vertices[v].co for v in tri.vertices]
            rotations=[]
            for shift in range(3):rotations.append(max((positions[(j+shift)%3]-Vector(wanted['positions'][j])).length for j in range(3)))
            shift=rotations.index(min(rotations));error=rotations[shift];position_error=max(position_error,error);order_bad+=error>2e-5
            mat=m.materials[m.polygons[tri.polygon_index].material_index].name.split('.')[0]
            material_mismatch+=mat!=wanted['material']
            a,b,c=positions;physical_bad+=(b-a).cross(c-a).length_squared<=1e-16
            for layer_index,layer in enumerate(m.uv_layers):
                values=[tuple(layer.data[loop].uv) for loop in tri.loops]
                a,b,c=values;ab=(b[0]-a[0],b[1]-a[1]);ac=(c[0]-a[0],c[1]-a[1]);cross=abs(ab[0]*ac[1]-ab[1]*ac[0])
                uv_bad[layer.name]+=cross<=1e-14;uv_min[layer.name]=min(uv_min[layer.name],cross)
                for j in range(3):
                    actual=values[(j+shift)%3];target=wanted['uvs'][layer_index][j]
                    uv_exact=uv_exact and all(float(x).hex()==float(y).hex() for x,y in zip(actual,target))
                    uv_error=max(uv_error,max(abs(x-y) for x,y in zip(actual,target)))
            for j in range(3):
                actual=(normal_matrix@m.corner_normals[tri.loops[(j+shift)%3]].vector).normalized();target=Vector(wanted['normals'][j])
                angle=math.degrees(math.atan2(actual.cross(target).length,actual.dot(target)));normal_angle=max(normal_angle,angle)
        reports.append({'name':o.name,'triangles':len(source),'triangleOrderMismatch':order_bad,'maxWorldPositionDeviationMetres':position_error,'cornerUvFloat32BitsExact':uv_exact,'maxUvComponentDeviation':uv_error,'materialMismatch':material_mismatch,'maxWorldNormalAngularDeviationDegreesFromV7':normal_angle,'physicalFailures':physical_bad,'uvFailures':uv_bad,'uvMinimumCross':uv_min})
finally:
    for o in created:bpy.data.objects.remove(o,do_unlink=True)
    for m in set(bpy.data.meshes)-meshes_before:
        if m.users==0:bpy.data.meshes.remove(m)
    for o,name in original_names.items():o.name=name
passed=all(r['triangleOrderMismatch']==r['materialMismatch']==r['physicalFailures']==0 and all(v==0 for v in r['uvFailures'].values()) for r in reports)
print('GARAGE_V7_ROUNDTRIP '+json.dumps({'passed':passed,'objects':reports,'meshes':len(reports),'triangles':sum(r['triangles'] for r in reports),'allTriangleOrdersPreserved':all(r['triangleOrderMismatch']==0 for r in reports),'allCornerUvBitsExact':all(r['cornerUvFloat32BitsExact'] for r in reports),'maxWorldPositionDeviationMetres':max(r['maxWorldPositionDeviationMetres'] for r in reports),'maxUvComponentDeviation':max(r['maxUvComponentDeviation'] for r in reports),'maxWorldNormalAngularDeviationDegreesFromV7':max(r['maxWorldNormalAngularDeviationDegreesFromV7'] for r in reports),'physicalFailures':sum(r['physicalFailures'] for r in reports),'uvFailures':sum(sum(r['uvFailures'].values()) for r in reports),'visualAccepted':False}))
assert passed,'FBX roundtrip has an ordering/material/geometry/UV failure'
