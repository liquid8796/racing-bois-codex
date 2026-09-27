"""Designed closed tank loft: smooth underside arch and setback neck; no Boolean cuts."""
import bpy,bmesh,math,json
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from mathutils.bvhtree import BVHTree
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
assert bpy.data.filepath.replace('\\','/').endswith('/Spark/V2/RB_Golden_Spark_v2_refined05.blend')
root=bpy.data.objects['RB_Golden_Spark_v2'];scene=bpy.context.scene
for trial in list(root.children_recursive):
    if trial.name.startswith('V2 continuous tank surface06'):bpy.data.objects.remove(trial,do_unlink=True)
old=bpy.data.objects['V2 copper teardrop tank']
held={}
for obj in root.children_recursive:
    if obj.type=='MESH' and obj!=old and obj.name not in ['Tank filler rubber gasket','Flush silver fuel cap']:
        held[obj.name]=([tuple(v.co) for v in obj.data.vertices],[tuple(f.vertices) for f in obj.data.polygons],
            [tuple(row) for row in obj.matrix_world],[material.name for material in obj.data.materials])
markers={obj.name:list(obj.matrix_world.translation) for obj in root.children_recursive if obj.type=='EMPTY'}

# Nominal Y, continuous lower flank, crown and half-width. Dimensions are authored,
# not inferred metric measurements of an uncalibrated concept image.
sections=[(-.117,.840,.856,.030),(-.072,.824,.892,.082),(.015,.809,.964,.151),
    (.125,.806,1.004,.194),(.242,.809,1.001,.198),(.323,.842,.969,.162),
    (.367,.902,.934,.091),(.400,.902,.913,.028)]
xs=[row[0] for row in sections]

def slopes(values):
    h=[xs[i+1]-xs[i] for i in range(len(xs)-1)]
    secants=[(values[i+1]-values[i])/h[i] for i in range(len(h))]
    result=[secants[0]]
    for i in range(1,len(xs)-1):
        left,right=secants[i-1],secants[i]
        if left*right<=0:result.append(0)
        else:
            w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1]
            result.append((w1+w2)/(w1/left+w2/right))
    result.append(secants[-1]);return result

fields=[[row[i] for row in sections] for i in [1,2,3]]
derivatives=[slopes(values) for values in fields]

def sample(field,segment,t):
    values=fields[field];m=derivatives[field];h=xs[segment+1]-xs[segment]
    return (2*t*t*t-3*t*t+1)*values[segment]+(t*t*t-2*t*t+t)*h*m[segment]+(-2*t*t*t+3*t*t)*values[segment+1]+(t*t*t-t*t)*h*m[segment+1]

def ease(value):
    t=max(0,min(1,value));return t*t*(3-2*t)

vertices=[];parameters=[];faces=[];sides=64;samples=10;rings=[]
for segment in range(len(sections)-1):
    for step in range(samples):
        t=step/samples;y=xs[segment]+(xs[segment+1]-xs[segment])*t
        rings.append((y,sample(0,segment,t),sample(1,segment,t),sample(2,segment,t)))
rings.append(tuple(sections[-1]))
for ring,(y,bottom,top,width) in enumerate(rings):
    arch=min(top-.008,max(bottom+.004,.814+.245*y))
    half=[(0,top),(.38*width,bottom+.993*(top-bottom)),(.69*width,bottom+.944*(top-bottom)),
        (.91*width,bottom+.809*(top-bottom)),(width,bottom+.58*(top-bottom)),(width,bottom+.32*(top-bottom)),
        (.965*width,bottom+.077*(top-bottom)),(.82*width,arch),(0,min(top-.007,arch+.003))]
    controls=half+[(-x,z) for x,z in reversed(half[1:-1])]
    for j in range(sides):
        part=j//4;t=(j%4)/4
        a,b,c,d=[Vector(controls[k%16]) for k in [part-1,part,part+1,part+2]]
        p=.5*(2*b+(c-a)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
        # A broad continuous front wall returns behind the steering axis; it is not a cut-out surface.
        setback=.080*ease((y-.180)/.220)*math.exp(-(p.x/.075)**2)
        vertices.append((p.x,y-setback,p.y));parameters.append((.05+.90*(y-xs[0])/(xs[-1]-xs[0]),j/sides))
    if ring:faces.extend(((ring-1)*sides+j,(ring-1)*sides+(j+1)%sides,ring*sides+(j+1)%sides,ring*sides+j) for j in range(sides))

for start in [0,(len(rings)-1)*sides]:
    projected=[Vector((vertices[start+i][0],vertices[start+i][2],0)) for i in range(sides)]
    triangles=tessellate_polygon([projected])
    for triangle in triangles:
        assert all(isinstance(index,int) and 0<=index<sides for index in triangle)
        faces.append(tuple(start+index for index in triangle))

data=bpy.data.meshes.new('V2 continuous tank surface06 mesh');data.from_pydata(vertices,[],faces);data.update()
tank=bpy.data.objects.new('V2 continuous tank surface06',data);scene.collection.objects.link(tank);tank.parent=root;tank['asset_group']='Body'
data.materials.append(bpy.data.materials['Spark_Copper']);uv=data.uv_layers.new(name='UV0_ContinuousTank')
quad_count=(len(rings)-1)*sides
for face in data.polygons:
    face.use_smooth=True
    wrap=len(face.vertices)==4 and any(i%sides==0 for i in face.vertices) and any(i%sides==sides-1 for i in face.vertices)
    for loop in face.loop_indices:
        index=data.loops[loop].vertex_index;u,v=parameters[index]
        if face.index>=quad_count:
            point=data.vertices[index].co;uv.data[loop].uv=(.020+point.x*.08,.50+point.z*.08)
        else:
            if wrap and index%sides==0:v=1
            uv.data[loop].uv=(u,v)
bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.update()
bpy.context.view_layer.update();data.calc_loop_triangles();uv=data.uv_layers.active
bad=uv_bad=0
for tri in data.loop_triangles:
    a,b,c=[data.vertices[i].co for i in tri.vertices];bad+=(b-a).cross(c-a).length_squared<=1e-16
    a,b,c=[uv.data[i].uv for i in tri.loops];uv_bad+=abs((b.x-a.x)*(c.y-a.y)-(c.x-a.x)*(b.y-a.y))<=2e-12
bm=bmesh.new();bm.from_mesh(data);nonmanifold=sum(not edge.is_manifold for edge in bm.edges);bm.free()
def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(f.vertices) for f in obj.data.polygons],all_triangles=False,epsilon=0)
tank_tree=tree(tank);contacts=[]
for name in ['Steering head','Upper triple clamp','Lower triple clamp','Upper black frame rail -1','Upper black frame rail 1','V2 shaped leather saddle']:
    contacts.append({'object':name,'surfaceIntersections':len(tank_tree.overlap(tree(bpy.data.objects[name])))})
valid=bad==0 and uv_bad==0 and nonmanifold==0 and all(row['surfaceIntersections']==0 for row in contacts)
source=None
if valid:
    bpy.data.objects.remove(old,do_unlink=True);tank.name='V2 copper teardrop tank'
    hit,point,normal,index=tank.ray_cast(Vector((0,.239,2)),Vector((0,0,-1)));assert hit
    gasket=bpy.data.objects['Tank filler rubber gasket'];current=min((gasket.matrix_world@v.co).z for v in gasket.data.vertices)
    for name in ['Tank filler rubber gasket','Flush silver fuel cap']:bpy.data.objects[name].location.z+=point.z-current
    bpy.context.view_layer.update()
    for name,before in held.items():
        obj=bpy.data.objects[name]
        after=([tuple(v.co) for v in obj.data.vertices],[tuple(f.vertices) for f in obj.data.polygons],
            [tuple(row) for row in obj.matrix_world],[material.name for material in obj.data.materials])
        assert before==after,'A non-tank component changed: '+name
    assert markers=={obj.name:list(obj.matrix_world.translation) for obj in root.children_recursive if obj.type=='EMPTY'}
    seat=bpy.data.objects['V2 shaped leather saddle'];hit,seat_point,normal,index=seat.ray_cast(Vector((0,-.340,2)),Vector((0,0,-1)))
    assert hit and abs(seat_point.z-.800)<=.00001
    source='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_refined06.blend'
    bpy.ops.wm.save_as_mainfile(filepath=source,compress=True)
else:
    tank.hide_render=True;tank.hide_set(True)
print('SPARK_V2_TANK06='+json.dumps({'source':source,'saved':valid,'tankVertices':len(data.vertices),'tankTriangles':len(data.loop_triangles),
    'physicalTriangleFailures':bad,'uvTriangleFailures':uv_bad,'nonmanifoldEdges':nonmanifold,'contacts':contacts,
    'preservedOtherMeshCount':len(held),'canonicalMarkersUnchanged':valid,'noBooleanModifiers':True,'visualAccepted':False,'exported':False}))
