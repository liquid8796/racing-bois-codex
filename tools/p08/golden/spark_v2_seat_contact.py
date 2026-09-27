"""Place a rib crest at the canonical seat contact without moving the contact marker or base cushion profile."""
import bpy,bmesh,math,json
from mathutils import Vector
assert bpy.data.filepath.replace('\\','/').endswith('/Spark/V2/RB_Golden_Spark_v2_refined04.blend')
seat=bpy.data.objects['V2 shaped leather saddle'];data=seat.data
profile_z=[1,.989,.935,.77,.40,.09,0,0,0,.09,.40,.77,.935,.989]
ring_vertices=(8-1)*24*14+14
assert len(data.vertices)==ring_vertices+2
before_hit,before,normal,index=seat.ray_cast(Vector((0,-.340,2)),Vector((0,0,-1)))
for vertex in list(data.vertices)[:ring_vertices]:
    y=vertex.co.y;weight=max(0,min(1,(profile_z[vertex.index%14]-.52)/.40))
    old=.0027*math.exp(-(math.sin(math.pi*(y+.948)/.032)/.25)**2)*weight
    new=.0027*math.exp(-(math.sin(math.pi*(y+.932)/.032)/.25)**2)*weight
    vertex.co.z+=old-new
for cap,first in [(ring_vertices,0),(ring_vertices+1,ring_vertices-14)]:
    data.vertices[cap].co=sum((data.vertices[first+i].co for i in range(14)),Vector())/14
bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.update()
bpy.context.view_layer.update()
hit,point,normal,index=seat.ray_cast(Vector((0,-.340,2)),Vector((0,0,-1)))
assert hit and abs(point.z-.800)<=.00001,'Seat crest did not preserve canonical contact height'
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_refined05.blend',compress=True)
print('SPARK_V2_SEAT_CONTACT='+json.dumps({'source':bpy.data.filepath,'beforeSurfaceZ':before.z,'afterSurfaceZ':point.z,'contactMarkerUnchanged':True,
    'changedOnly':'Rib phase shifted by half the existing 0.032m period; base cushion sections and canonical contact marker unchanged',
    'visualAccepted':False,'exported':False}))
