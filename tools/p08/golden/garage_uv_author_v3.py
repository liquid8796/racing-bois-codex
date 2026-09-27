"""Author a dedicated non-overlapping lightmap channel without changing UV0 or topology."""
import bpy,math,json
ROOT='D:/Project/Unity/racing-bois/'
assert '/Garage/V2/' in bpy.data.filepath.replace('\\','/')
root=bpy.data.objects['RB_Golden_Garage'];rows=[];states=[]
def object_name(o):return o.name
for o in sorted(root.children_recursive,key=object_name):
    if o.type!='MESH' or '_L0_' not in o.name:continue
    m=o.data;m.calc_loop_triangles();assert m.uv_layers[0].name!='LightmapUV'
    before=([tuple(v.co) for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],
            [tuple(p.uv) for p in m.uv_layers[0].data],[tuple(n.vector) for n in m.corner_normals])
    states.append((o,o.hide_get(),o.hide_render));bpy.ops.object.select_all(action='DESELECT')
    o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
    layer=m.uv_layers.get('LightmapUV') or m.uv_layers.new(name='LightmapUV');m.uv_layers.active=layer
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025,area_weight=1.0,correct_aspect=False,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT');m.calc_loop_triangles();layer=m.uv_layers.get('LightmapUV')
    after=([tuple(v.co) for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],
           [tuple(p.uv) for p in m.uv_layers[0].data],[tuple(n.vector) for n in m.corner_normals])
    assert before==after,'Geometry/UV0/normals changed '+o.name
    minimum=1;bad=0;uvtriangles=[]
    for tri in m.loop_triangles:
        values=[tuple(layer.data[i].uv) for i in tri.loops];uvtriangles.append(values)
        a,b,c=values;area=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]));minimum=min(minimum,area);bad+=area<=1e-14
    assert bad==0,'Degenerate second UVs '+o.name
    assert all(math.isfinite(v) and 0<=v<=1 for triangle in uvtriangles for corner in triangle for v in corner),'Invalid UV range'
    rows.append({'name':o.name,'triangles':len(uvtriangles),'degenerateUvTriangles':bad,'minimumUvCross':minimum,
                 'geometryUv0NormalsUnchanged':before==after,'uvTriangles':uvtriangles})
    m.uv_layers.active_index=0;m.uv_layers[0].active_render=True
for o,hidden,render_hidden in states:o.hide_set(hidden);o.hide_render=render_hidden
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V3/RB_Golden_Garage.blend')
print('GARAGE_LIGHTMAP_UV '+json.dumps({'meshes':rows,'savedSource':'ArtSource/P08/Golden/Garage/V3/RB_Golden_Garage.blend','visualAccepted':False}))
