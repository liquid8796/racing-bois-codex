"""Materialize the already-audited V5 loop-triangle stream verbatim.

No triangulation modifier/operator, UV remap, vertex weld or normal
recalculation substitutes for the measured source corner data.
"""
import bpy,math,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/Garage/V5/RB_Golden_Garage.blend'),'Load the frozen baseline V5'
root=bpy.data.objects['RB_Golden_Garage'];rows=[]

def floats(values):
    # Float32 values promote exactly to Python floats; hex also distinguishes
    # signed zero. This is an injective finite-value comparison without a
    # native struct/hash module (which the pinned safe mode does not allow).
    return tuple(float(component).hex() for value in values for component in value)

for o in root.children_recursive:
    if o.type!='MESH':continue
    assert not o.modifiers and not o.vertex_groups and not o.data.color_attributes,o.name
    old=o.data;old.calc_loop_triangles();positions=[tuple(v.co) for v in old.vertices]
    triangles=[tuple(t.vertices) for t in old.loop_triangles]
    source_loops=[tuple(t.loops) for t in old.loop_triangles]
    materials=list(old.materials);material_ids=[old.polygons[t.polygon_index].material_index for t in old.loop_triangles]
    smooth=[old.polygons[t.polygon_index].use_smooth for t in old.loop_triangles]
    source_normals=[tuple(old.corner_normals[loop].vector) for loops in source_loops for loop in loops]
    source_uvs={layer.name:[tuple(layer.data[loop].uv) for loops in source_loops for loop in loops] for layer in old.uv_layers}
    active_uv=old.uv_layers.active.name;render_uv=next((u.name for u in old.uv_layers if u.active_render),active_uv)
    matrix=tuple(tuple(row) for row in o.matrix_world)
    new=bpy.data.meshes.new(old.name+'_ExplicitV7')
    new.from_pydata(positions,[],triangles);new.update()
    assert len(new.polygons)==len(triangles) and len(new.loops)==len(triangles)*3,o.name
    for material in materials:new.materials.append(material)
    for i,p in enumerate(new.polygons):p.material_index=material_ids[i];p.use_smooth=smooth[i]
    for name,values in source_uvs.items():
        layer=new.uv_layers.new(name=name,do_init=False)
        for index,value in enumerate(values):layer.data[index].uv=value
        layer.active_render=name==render_uv
    new.uv_layers.active_index=list(source_uvs).index(active_uv)
    o.data=new;new.normals_split_custom_set(source_normals);new.update();bpy.context.view_layer.update()
    assert floats([tuple(v.co) for v in new.vertices])==floats(positions),'Position bits changed: '+o.name
    assert [tuple(p.vertices) for p in new.polygons]==triangles,'Triangle stream changed: '+o.name
    assert [p.material_index for p in new.polygons]==material_ids,'Material assignment changed: '+o.name
    assert tuple(tuple(row) for row in o.matrix_world)==matrix,'Object transform changed: '+o.name
    uv_exact={}
    for layer in new.uv_layers:
        uv_exact[layer.name]=floats([tuple(v.uv) for v in layer.data])==floats(source_uvs[layer.name])
    assert all(uv_exact.values()),'Corner UV bits changed: '+o.name
    actual_normals=[tuple(n.vector) for n in new.corner_normals]
    max_component=0;max_angle=0;angle_sum=0
    for wanted,actual in zip(source_normals,actual_normals):
        max_component=max(max_component,max(abs(a-b) for a,b in zip(wanted,actual)))
        a=Vector(wanted);b=Vector(actual);angle=math.degrees(math.atan2(a.cross(b).length,a.dot(b)));max_angle=max(max_angle,angle);angle_sum+=angle*angle
    new.calc_loop_triangles();physical_bad=0;uv_bad={name:0 for name in source_uvs};uv_min={name:1 for name in source_uvs}
    for tri in new.loop_triangles:
        a,b,c=[new.vertices[i].co for i in tri.vertices]
        physical_bad+=(o.matrix_world.to_3x3()@(b-a)).cross(o.matrix_world.to_3x3()@(c-a)).length_squared<=1e-16
        for layer in new.uv_layers:
            a,b,c=[layer.data[i].uv for i in tri.loops];ab=b-a;ac=c-a;cross=abs(ab.x*ac.y-ab.y*ac.x)
            uv_bad[layer.name]+=cross<=1e-14;uv_min[layer.name]=min(uv_min[layer.name],cross)
    rows.append({'name':o.name,'vertices':len(positions),'sourcePolygons':len(old.polygons),'explicitTriangles':len(triangles),'positionFloat32BitsExact':True,'sourceLoopTriangleOrderExact':True,'perTriangleMaterialsExact':True,'transformsExact':True,'cornerUvFloat32BitsExact':uv_exact,'normalFloat32BitsExact':floats(actual_normals)==floats(source_normals),'normalMaxComponentDeviation':max_component,'normalMaxAngularDeviationDegrees':max_angle,'normalRmsAngularDeviationDegrees':math.sqrt(angle_sum/len(actual_normals)),'physicalFailures':physical_bad,'uvFailures':uv_bad,'uvMinimumCross':uv_min})
    assert physical_bad==0 and all(v==0 for v in uv_bad.values()),'Explicit source triangle gate failed: '+o.name
scene=bpy.context.scene
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V7/RB_Golden_Garage.blend')
print('GARAGE_V7_EXPLICIT_TRIANGLES '+json.dumps({'objects':rows,'meshCount':len(rows),'triangles':sum(r['explicitTriangles'] for r in rows),'positionsUvMaterialsTransformsExact':True,'allNormalsBitExact':all(r['normalFloat32BitsExact'] for r in rows),'maximumNormalComponentDeviation':max(r['normalMaxComponentDeviation'] for r in rows),'maximumNormalAngularDeviationDegrees':max(r['normalMaxAngularDeviationDegrees'] for r in rows),'sourceV5Modified':False,'visualAccepted':False}))
