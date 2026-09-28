"""Use a slimmer lamp surround and fit the cowl cheek to actual fairing boundaries (study22 flared out)."""
import bpy
import bmesh
import json
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/R6/RB_Golden_Apex_r6_editable22.blend')
root=bpy.data.objects['RB_Golden_Apex_r6']

def filleted(points):
    result=[]
    for i,raw in enumerate(points):
        p=Vector(raw);a=p+(Vector(points[(i-1)%len(points)])-p)*.10;b=p+(Vector(points[(i+1)%len(points)])-p)*.10
        for j in range(5):
            t=j/4;result.append(a*(1-t)**2+p*2*t*(1-t)+b*t*t)
        end=Vector(points[(i+1)%len(points)])+(p-Vector(points[(i+1)%len(points)]))*.10
        for j in range(1,4):result.append(b*(1-j/4)+end*(j/4))
    return result

def update(obj):
    obj.data.update();bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert sum(not edge.is_manifold for edge in bm.edges)==0,obj.name
    bm.to_mesh(obj.data);bm.free();obj.data.update();obj.data.normals_split_custom_set([(0,0,0)]*len(obj.data.loops))

target=filleted([(.007,.752),(.009,.837),(.147,.877),(.234,.870),(.232,.808),(.170,.774)])
rows=[]
for side in [-1,1]:
    obj=bpy.data.objects['R4 swept continuous optical cowl '+str(side)];data=obj.data;n=48
    assert len(data.vertices)==672
    previous=[obj.matrix_world@vertex.co for vertex in data.vertices];inverse=obj.matrix_world.inverted()
    outer=[Vector((side*target[j].x,previous[j].y,target[j].y)) for j in range(n)]
    inner=[previous[6*n+j].copy() for j in range(n)]
    for p in inner:p.x-=side*.010*max(0,min(1,(.10-abs(p.x))/.070))
    for vertex in data.vertices:
        layer=vertex.index//336;within=vertex.index%336;k=within//n;j=within%n;t=k/6
        point=outer[j].lerp(inner[j],t);point.y-=layer*.004
        vertex.co=inverse@point
    update(obj)
    # All aperture components follow the same small inward-edge expansion.
    for component in root.children_recursive:
        if component.type!='MESH' or not any(component.name.startswith(prefix) for prefix in ['R4 recessed optical seal','R4 headlamp aperture depth','R4 closed black lamp back','R4 flush swept clear lens']):continue
        if not component.name.endswith(' '+str(side)):continue
        world=component.matrix_world;inv=world.inverted()
        for vertex in component.data.vertices:
            p=world@vertex.co;p.x-=side*.010*max(0,min(1,(.10-abs(p.x))/.070));vertex.co=inv@p
        update(component)
    gasket=bpy.data.objects['R6 thin lamp aperture gasket '+str(side)]
    band_outer=[];band_inner=[]
    for j in range(n):
        a=obj.matrix_world@data.vertices[5*n+j].co;b=obj.matrix_world@data.vertices[6*n+j].co
        band_outer.append(a.lerp(b,.66));band_inner.append(b)
    inverse=gasket.matrix_world.inverted()
    for vertex in gasket.data.vertices:
        layer=vertex.index//96;within=vertex.index%96
        p=(band_outer+band_inner)[within].copy();p.y+=.0015 if layer==0 else .0003;vertex.co=inverse@p
    update(gasket)
    shoulder=bpy.data.objects['R4 integrated formed cowl shoulder '+str(side)]
    for vertex in shoulder.data.vertices:
        index=vertex.index%117;t=(index//13)/8;u=(index%13)/12
        vertex.co.z-=.010*(1-t)*(1-u)
    update(shoulder)

    fairing=bpy.data.objects['R4 formed main fairing with through intake '+str(side)]
    points=[fairing.matrix_world@vertex.co for vertex in fairing.data.vertices]
    def boundary(y,z):
        distance=min((p.y-y)**2+(p.z-z)**2 for p in points)
        candidates=[p for p in points if (p.y-y)**2+(p.z-z)**2<=distance+.000004]
        best=candidates[0]
        for p in candidates:
            if side*p.x>side*best.x:best=p
        assert distance<.0005,'Requested actual fairing boundary unavailable'
        return best.copy()
    a=Vector((side*.232,.774,.808));b=Vector((side*.170,.806,.774));c=boundary(.649,.715);d=boundary(.765,.840)
    cheek=bpy.data.objects['R6 moulded lower optical cheek '+str(side)];inverse=cheek.matrix_world.inverted()
    for vertex in cheek.data.vertices:
        layer=vertex.index//81;within=vertex.index%81;t=(within//9)/8;u=(within%9)/8
        p=a*(1-u)*(1-t)+b*u*(1-t)+c*u*t+d*(1-u)*t;p.x-=side*layer*.004
        vertex.co=inverse@p
    update(cheek)
    rows.append({'side':side,'actualCheekBoundaryLower':list(c),'actualCheekBoundaryUpper':list(d),'slimmerOpticalSurround':True})

chin=bpy.data.objects['R4 continuous lower nose return']
for vertex in chin.data.vertices:
    index=vertex.index%147;row=index//49;x=abs(vertex.co.x)
    z=.752 if x<=.007 else .752+(.774-.752)*(x-.007)/.163 if x<=.170 else .774+(.808-.774)*(x-.170)/.062
    vertex.co.z=z-row*.002
update(chin)
root['r6Phase']='Cowl24: reduced pearl margins, dark aperture detail and actual-boundary fitted cheeks; no added flare'
root['visualAccepted']=False
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable24.blend')
print('R6_COWL24='+json.dumps({'sides':rows,'saved':bpy.data.filepath,'visualAccepted':False}))
