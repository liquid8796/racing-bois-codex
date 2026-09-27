"""Refit equipment to actual source surfaces after inspection of V2 renders."""
import bpy,bmesh,math,random,json
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];body=bpy.data.objects['AshV2_Body'];clothes=bpy.data.objects['AshV2_Clothes'];shoes=bpy.data.objects['AshV2_Shoes']
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
PREFIX='RB_P06_Rider_L0_';black=bpy.data.materials['AshV2_CharcoalLeather'];brown=bpy.data.materials['AshV2_BootLeather'];metal=bpy.data.materials['AshV2_AgedBrass'];thread=bpy.data.materials['AshV2_OchreThread']
def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
trees={}
for source in [body,clothes,shoes]:
    tree=KDTree(len(source.data.vertices))
    for vertex in source.data.vertices:tree.insert(vertex.co,vertex.index)
    tree.balance();trees[source.name]=tree
def weights(obj,source=body,role=None):
    cache={}
    for vertex in obj.data.vertices:
        if role:values=[(PREFIX+role,1)]
        else:
            p,index,d=trees[source.name].find(vertex.co)
            values=[(source.vertex_groups[g.group].name,g.weight) for g in source.data.vertices[index].groups if source.vertex_groups[g.group].name.startswith(PREFIX) and g.weight>.00001]
        total=sum(w for n,w in values)
        for name,value in values:
            if name not in cache:cache[name]=obj.vertex_groups.new(name=name)
            cache[name].add([vertex.index],value/total,'REPLACE')
    modifier=obj.modifiers.new('Ash anatomical Generic deformation','ARMATURE');modifier.object=rig
def mesh(name,vertices,faces,mat,source=body,role=None):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.parent=rig;data.materials.append(mat)
    for face in data.polygons:face.use_smooth=True
    active(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
    weights(obj,source,role);return obj
def solid(obj,thickness):
    active(obj);mod=obj.modifiers.new('Leather edge return','SOLIDIFY');mod.thickness=thickness;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
def tube(name,points,radius,mat,source=body,role=None,sides=6):
    vertices=[];faces=[]
    for i,p in enumerate(points):
        p=Vector(p);t=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).normalized();helper=Vector((0,0,1)) if abs(t.z)<.9 else Vector((1,0,0));a=t.cross(helper).normalized();b=t.cross(a).normalized()
        for j in range(sides):
            angle=math.tau*j/sides;vertices.append(p+radius*(a*math.cos(angle)+b*math.sin(angle)))
            if i:faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,vertices,faces,mat,source,role)
def front_point(x,z,offset):
    hit,p,n,index=clothes.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))
    if not hit:raise RuntimeError('Front panel outside clothing '+str((x,z)))
    return p+n*offset
def leg_center(side,z):
    knee=rig.data.bones[PREFIX+'Shin_'+side].head_local
    bone=rig.data.bones[PREFIX+('Thigh_' if z>knee.z else 'Shin_')+side]
    a=bone.head_local;b=bone.tail_local;t=max(0,min(1,(z-a.z)/(b.z-a.z)))
    return a.x+(b.x-a.x)*t

for obj in list(scene.objects):
    if obj.name.startswith(('AshV2_BootStrap_','AshV2_BootBuckle','AshV2_KneeProtection_','AshV2_KneeAccordion_','AshV2_ChinStrap','AshV2_StandCollar','AshV2_CollarTopStitch')):bpy.data.objects.remove(obj,do_unlink=True)
# Refitted knee pieces use ray projection, keeping the intended width/height;
# nearest-surface projection previously collapsed the visible width.
for side,sign in [('L',1),('R',-1)]:
    knee=rig.data.bones[PREFIX+'Shin_'+side].head_local
    rows=9;cols=11;vertices=[];faces=[]
    for r in range(rows):
        v=-1+2*r/(rows-1);halfwidth=.045*(.83+.17*math.sqrt(max(0,1-v*v)))
        for c in range(cols):
            u=-1+2*c/(cols-1);height=knee.z+v*.069
            vertices.append(front_point(leg_center(side,height)+u*halfwidth,height,.004+.003*(1-u*u)*(1-v*v)))
            if r and c:
                i=r*cols+c;faces.append((i-cols-1,i-cols,i,i-1))
    pad=mesh('AshV2_KneeProtection_'+side,vertices,faces,black,clothes);solid(pad,.002)
    boundary=vertices[:cols]+[vertices[r*cols+cols-1] for r in range(1,rows)]+list(reversed(vertices[-cols:-1]))+[vertices[r*cols] for r in range(rows-2,0,-1)]
    tube('AshV2_KneeStitch_'+side,boundary+[boundary[0]],.0006,thread,clothes,sides=4)
    for i in range(8):
        z=knee.z+.085+i*.010
        path=[front_point(leg_center(side,z)-.046+j*.092/14,z,.003+.001*math.sin(j*math.pi/14)) for j in range(15)]
        tube('AshV2_KneeAccordion_'+side,path,.0023,black,clothes,sides=6)

# Boot belts now hug the actual shoe/shaft mesh and inherit its skin weights.
for side,sign in [('L',1),('R',-1)]:
    ankle=rig.data.bones[PREFIX+'Foot_'+side].head_local
    for height in [.124,.203,.260]:
        vertices=[];faces=[];count=64
        for i in range(count):
            angle=math.tau*i/count;radial=Vector((math.sin(angle),-math.cos(angle),0))
            for j in range(2):
                z=height+(j-.5)*(.016 if height<.25 else .021)
                origin=Vector((ankle.x,ankle.y,z))+radial*.35
                hit,p,n,index=shoes.ray_cast(origin,-radial)
                if not hit:raise RuntimeError('Boot belt outside shaft '+str((side,height,i)))
                vertices.append(p+n*.0023)
            nxt=(i+1)%count;faces.append((i*2,nxt*2,nxt*2+1,i*2+1))
        belt=mesh('AshV2_BootStrap_'+side,vertices,faces,brown,shoes);solid(belt,.002)
        if height<.25:
            index=count//4 if sign>0 else count*3//4
            center=(Vector(vertices[index*2])+Vector(vertices[index*2+1]))*.5+Vector((sign*.0015,0,0))
            corners=[center+Vector((0,-.012,-.010)),center+Vector((0,.012,-.010)),center+Vector((0,.012,.010)),center+Vector((0,-.012,.010))]
            tube('AshV2_BootBuckle_'+side,corners+[corners[0]],.0018,metal,shoes,sides=6)
            tube('AshV2_BootBucklePin_'+side,[center+Vector((0,-.012,0)),center+Vector((0,.010,0))],.001,metal,shoes,sides=6)
brown.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.66

# Skin-hugging collar: use the actual neck/clothing radial intersection for
# every sample instead of fitting an arbitrary ellipse around the character.
vertices=[];faces=[];count=64
for r in range(4):
    t=r/3;z=1.535+t*.032
    for i in range(count):
        angle=.065+(math.tau-.13)*i/(count-1);radial=Vector((math.sin(angle),-math.cos(angle),0));origin=Vector((0,-.008,z))+radial*.5
        hit,p,n,index=body.ray_cast(origin,-radial)
        if not hit:raise RuntimeError('Collar neck ray missed')
        offset=.006+(1-t)*.005;vertices.append(p+n*offset)
        if r and i:
            k=r*count+i;faces.append((k-count-1,k-count,k,k-1))
collar=mesh('AshV2_StandCollar',vertices,faces,black,body);solid(collar,.0025)
tube('AshV2_CollarTopStitch',vertices[-count:],.0006,thread,body,sides=4)

# Chinstrap follows a smooth jaw path and sits behind the front chin contour.
for side in [-1,1]:
    controls=[Vector((side*.103,-.023,1.620)),Vector((side*.090,-.053,1.590)),Vector((side*.060,-.081,1.566)),Vector((0,-.077,1.560))]
    points=[]
    for i in range(len(controls)-1):
        p0=controls[max(0,i-1)];p1=controls[i];p2=controls[i+1];p3=controls[min(i+2,len(controls)-1)]
        for k in range(10):
            t=k/10;points.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    points.append(controls[-1]);vertices=[];faces=[]
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized();across=tangent.cross(Vector((0,-1,0))).normalized()*.0045
        vertices.extend([p-across,p+across])
        if i:faces.append(((i-1)*2,(i-1)*2+1,i*2+1,i*2))
    strap=mesh('AshV2_ChinStrap_Fitted',vertices,faces,brown,role='Head');solid(strap,.0018)

# Dark amber physical absorption prevents the helmet backing from turning the
# transparent goggle lenses white in the studio render.
glass=bpy.data.materials['AshV2_AmberLens'];nodes=glass.node_tree.nodes;links=glass.node_tree.links;p=nodes['Principled BSDF']
p.inputs['Base Color'].default_value=(.19,.071,.012,1);p.inputs['Transmission Weight'].default_value=.92;p.inputs['Roughness'].default_value=.12
volume=nodes.new('ShaderNodeVolumeAbsorption');volume.inputs['Color'].default_value=(.35,.10,.022,1);volume.inputs['Density'].default_value=1200
links.new(volume.outputs[0],nodes['Material Output'].inputs['Volume'])
skin=bpy.data.materials['AshV2_Skin']
for node in skin.node_tree.nodes:
    if node.bl_idname=='ShaderNodeMixRGB' and node.blend_type=='MULTIPLY':node.inputs[2].default_value=(.59,.42,.28,1)

# Short curved fringe strands over the licensed scalp base. These are smooth
# tapered filament meshes following authored curl paths, not spike geometry.
hairmat=bpy.data.materials.new('AshV2_HairFibers');hairmat.use_nodes=True
p=hairmat.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.020,.011,.006,1);p.inputs['Roughness'].default_value=.46
rng=random.Random(170927)
for lock in range(18):
    x=-.074+lock*.148/17
    for strand in range(6):
        jitter=(strand-2.5)*.0009
        points=[]
        for step in range(14):
            t=step/13
            points.append((x+jitter+.008*math.sin(t*math.pi*1.4+lock*.4),-.072-.059*t+.004*math.sin(t*math.pi*2+strand*.25),1.794-.048*t+.005*math.sin(t*math.pi*2+lock*.65)))
        obj=tube('AshV2_ForelockFiber',points,.00030+rng.random()*.00010,hairmat,role='Head',sides=4)

bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print('ASH_V2_EQUIPMENT_FITTED_TO_ACTUAL_SURFACES')
