"""Export numeric LOD0 topology only through the direct Blender MCP session."""
import bpy,json
assert '/Garage/V2/' in bpy.data.filepath.replace('\\','/')
rows=[]
def object_name(o):return o.name
for o in sorted(bpy.data.objects['RB_Golden_Garage'].children_recursive,key=object_name):
    if o.type!='MESH' or '_L0_' not in o.name:continue
    m=o.data;m.calc_loop_triangles()
    rows.append({'name':o.name,'vertices':[list(v.co) for v in m.vertices],
                 'triangles':[list(t.vertices) for t in m.loop_triangles],
                 'loops':[list(t.loops) for t in m.loop_triangles],
                 'loopCount':len(m.loops)})
print('GARAGE_UV_TOPOLOGY '+json.dumps(rows))
