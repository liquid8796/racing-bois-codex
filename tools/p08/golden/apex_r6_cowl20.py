"""Re-form the high box-like R4 lamp cowl and short screen from the actual front/side comparison."""
import bpy
import bmesh
import json
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/R6/RB_Golden_Apex_r6_editable10.blend')
root=bpy.data.objects['RB_Golden_Apex_r6']
assert not root.get('r6_cowl20')
for name,count in [('R4 attached double-curved windscreen',1102),('R4 screen lower seated seal',332),('R4 fitted screen collar',290)]:
    assert len(bpy.data.objects[name].data.vertices)==count,name+' changed source topology'
for side in [-1,1]:
    for name,count in [('R4 screen thin side rim ',154),('R4 fitted windscreen side support ',228),('R4 integrated formed cowl shoulder ',234)]:
        assert len(bpy.data.objects[name+str(side)].data.vertices)==count

def height(z):
    knots=[(.775,.718),(.802,.740),(.828,.761),(.851,.780),(.887,.810),(.900,.821),(.928,.844),(.952,.867),(.966,.880),(.992,.902),(.997,.907)]
    if z<=knots[0][0]:return knots[0][1]+z-knots[0][0]
    for a,b in zip(knots,knots[1:]):
        if a[0]<=z<=b[0]:return a[1]+(b[1]-a[1])*(z-a[0])/(b[0]-a[0])
    return knots[-1][1]+z-knots[-1][0]

def corner(point):
    return .070*max(0,min(1,(point.y-.590)/.175))*max(0,min(1,(point.z-.720)/.120))

def screen_delta(q,t):
    base=.992-.040*q*q
    return (height(base)-base)*(1-t)-.032*q*q*t

skin_prefix=['R4 swept continuous optical cowl','R4 recessed optical seal','R4 headlamp aperture depth',
             'R4 closed black lamp back','R4 flush swept clear lens','R4 fitted central nose blade',
             'R4 continuous lower nose return','R4 fitted screen collar']
projector_prefix=['R4 machined projector ring','R4 luminous recessed projector']
rows=[]
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    name=obj.name
    kind=''
    if any(name.startswith(p) for p in skin_prefix):kind='optical-skin'
    elif any(name.startswith(p) for p in projector_prefix):kind='rigid-projector'
    elif name=='R4 attached double-curved windscreen':kind='screen'
    elif name=='R4 screen lower seated seal':kind='screen-base-seal'
    elif name.startswith('R4 screen thin side rim'):kind='screen-side-rim'
    elif name.startswith('R4 fitted windscreen side support'):kind='screen-support'
    elif name.startswith('R4 integrated formed cowl shoulder'):kind='shoulder'
    elif name.startswith('R4 formed main fairing') or name.startswith('R6 recessed front cooling return'):kind='upper-fairing-junction'
    elif name.startswith('R4 broad connected mirror arm') or name.startswith('R4 fairing mirror mount boot'):kind='mirror-base'
    if not kind:continue
    world=obj.matrix_world.copy();inverse=world.inverted();largest=0
    for vertex in obj.data.vertices:
        point=world@vertex.co;original=point.copy();side=1 if point.x>0 else -1
        if kind=='optical-skin':point.z=height(point.z)
        elif kind=='rigid-projector':point.z+=height(.887)-.887
        elif kind=='screen':
            index=vertex.index%551;t=(index//29)/18;q=(index%29)/14-1
            point.z+=screen_delta(q,t)
        elif kind=='screen-base-seal':
            index=vertex.index
            q=(index//10)/16-1 if index<330 else -1 if index==330 else 1
            point.z+=screen_delta(q,0)
        elif kind=='screen-side-rim':
            index=vertex.index;t=(index//8)/18 if index<152 else 0 if index==152 else 1
            point.z+=screen_delta(side,t)
        elif kind=='screen-support':
            index=vertex.index%114;t=(index//6)/18;u=(index%6)/5
            point.z+=screen_delta(side,t);point.x+=side*.010*(1-t)*u
        elif kind=='shoulder':
            index=vertex.index%117;t=(index//13)/8
            point.z+=(height(original.z)-original.z)*(1-t)
            point.x+=side*corner(original)*t
        elif kind=='upper-fairing-junction':point.x+=side*corner(point)
        elif kind=='mirror-base':point.z-=.026*max(0,min(1,(point.y-.490)/.077))
        vertex.co=inverse@point;largest=max(largest,(point-original).length)
    obj.data.update()
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    nonmanifold=sum(not edge.is_manifold for edge in bm.edges);assert nonmanifold==0,name+' closure changed'
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    obj.data.normals_split_custom_set([(0,0,0)]*len(obj.data.loops))
    rows.append({'name':name,'scope':kind,'maximumVertexChangeMetres':largest,'nonManifoldEdges':nonmanifold})
root['r6_cowl20']=True;root['visualAccepted']=False
root['r6Phase']='Cowl20: lower formed lamp envelope, rigid circular projector relocation, taller curved screen and joined upper-fairing shoulder'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable20.blend')
print('R6_COWL20='+json.dumps({'changed':rows,'saved':bpy.data.filepath,'projectorCenterHeight':height(.887),'screenCrownHeightRetained':1.125,'visualAccepted':False,'globalScalingApplied':False}))
