"""Refine actual V2 render findings: smooth panel masks, clothing fit, pads.

This is a source sculpt/material pass, not a visual-acceptance assertion.
"""
import bpy,bmesh,math,json
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
ROOT='D:/Project/Unity/racing-bois/'
scene=bpy.context.scene
rig=bpy.data.objects['RB_P06_Rider_Rig'];body=bpy.data.objects['AshV2_Body'];clothes=bpy.data.objects['AshV2_Clothes'];shoes=bpy.data.objects['AshV2_Shoes']
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
if body.data.shape_keys:
    for key in body.data.shape_keys.key_blocks:key.value=0
bpy.context.view_layer.update()
PREFIX='RB_P06_Rider_L0_'
black=bpy.data.materials['AshV2_CharcoalLeather'];brown=bpy.data.materials['AshV2_BootLeather'];rubber=bpy.data.materials['AshV2_Rubber'];metal=bpy.data.materials['AshV2_AgedBrass'];thread=bpy.data.materials['AshV2_OchreThread']
def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

# Hide covered anatomical faces without destroying expression vertex indices.
# The mask is applied on export/LOD copies after expressions are preserved.
group=body.vertex_groups.new(name='Ash_VisibleHeadNeck')
group.add([v.index for v in body.data.vertices if v.co.z>1.480],1,'REPLACE')
mask=body.modifiers.new('Covered anatomy removal','MASK');mask.vertex_group=group.name
active(body)
for i in range(len(body.modifiers)-1):bpy.ops.object.modifier_move_up(modifier=mask.name)

# Tailor trousers to the reference: taper the shin/ankle and sculpt folds
# around knees/ankles on the existing continuous garment topology.
for vertex in clothes.data.vertices:
    p=vertex.co
    if p.z<.94:
        side='L' if p.x>0 else 'R'
        bone=rig.data.bones[PREFIX+('Thigh_' if p.z>.54 else 'Shin_')+side]
        a=bone.head_local;b=bone.tail_local;axis=(b-a).normalized();t=max(0,min((p-a).dot(axis),(b-a).length));center=a+axis*t
        factor=.82 if p.z>.55 else .76
        p.x=center.x+(p.x-center.x)*factor;p.y=center.y+(p.y-center.y)*(.88 if p.z>.55 else .81)
        angle=math.atan2(p.y-center.y,p.x-center.x)
        influence=math.exp(-((p.z-.53)/.13)**2)+.65*math.exp(-((p.z-.28)/.07)**2)
        fold=.0016*influence*(math.sin(p.z*118+angle*2.1)+.4*math.sin(p.z*177-angle*3))
        p.x+=math.cos(angle)*fold;p.y+=math.sin(angle)*fold
bm=bmesh.new();bm.from_mesh(clothes.data)
remove=[f for f in bm.faces if all(v.co.z<.225 for v in f.verts)]
bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(clothes.data);bm.free();clothes.data.update()
for vertex in shoes.data.vertices:
    if vertex.co.z>.12:vertex.co.z=.12+(vertex.co.z-.12)*1.21
shoes.data.materials.append(rubber)
for polygon in shoes.data.polygons:
    if polygon.center.z<.046:polygon.material_index=1

# A stored rest-position attribute makes masks stable under skin deformation.
# Analytic stripe edges replace the rejected per-polygon stair-step boundary.
attr=clothes.data.attributes.get('AshRestPosition')
if attr is None:attr=clothes.data.attributes.new('AshRestPosition','FLOAT_VECTOR','POINT')
for vertex in clothes.data.vertices:attr.data[vertex.index].vector=vertex.co
for polygon in clothes.data.polygons:polygon.material_index=0
nodes=black.node_tree.nodes;links=black.node_tree.links;shader=nodes.get('Principled BSDF')
position=nodes.new('ShaderNodeAttribute');position.attribute_name='AshRestPosition'
sep=nodes.new('ShaderNodeSeparateXYZ');links.new(position.outputs['Vector'],sep.inputs[0])
x,y,z=sep.outputs[0],sep.outputs[1],sep.outputs[2]
def mathnode(operation,a,b=None):
    node=nodes.new('ShaderNodeMath');node.operation=operation
    for index,value in enumerate([a,b]):
        if value is None:continue
        if isinstance(value,(int,float)):node.inputs[index].default_value=value
        else:links.new(value,node.inputs[index])
    return node.outputs[0]
def vecnode(operation,a,b=None):
    node=nodes.new('ShaderNodeVectorMath');node.operation=operation
    for index,value in enumerate([a,b]):
        if value is None:continue
        if isinstance(value,(tuple,list,Vector)):node.inputs[index].default_value=value
        else:links.new(value,node.inputs[index])
    return node.outputs['Value'] if operation in ['DOT_PRODUCT','LENGTH','DISTANCE'] else node.outputs['Vector']
absx=mathnode('ABSOLUTE',x)
line=mathnode('ADD',mathnode('MULTIPLY',mathnode('SUBTRACT',absx,.10),.22),1.435)
front=mathnode('LESS_THAN',mathnode('ABSOLUTE',mathnode('SUBTRACT',z,line)),.014)
front=mathnode('MULTIPLY',front,mathnode('LESS_THAN',y,-.050))
front=mathnode('MULTIPLY',front,mathnode('GREATER_THAN',absx,.055))
front=mathnode('MULTIPLY',front,mathnode('LESS_THAN',absx,.272))
back=mathnode('LESS_THAN',mathnode('ABSOLUTE',mathnode('SUBTRACT',z,1.448)),.0155)
back=mathnode('MULTIPLY',back,mathnode('GREATER_THAN',y,.001))
back=mathnode('MULTIPLY',back,mathnode('LESS_THAN',absx,.275))
mask_signal=mathnode('MAXIMUM',front,back)
for side,sign in [('L',1),('R',-1)]:
    for part in ['UpperArm_','Forearm_']:
        bone=rig.data.bones[PREFIX+part+side];a=bone.head_local;axis=(bone.tail_local-a).normalized()
        outward=Vector((sign,0,0));outward=(outward-axis*outward.dot(axis)).normalized()
        delta=vecnode('SUBTRACT',position.outputs['Vector'],a)
        projection=vecnode('DOT_PRODUCT',delta,axis)
        scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[0].default_value=axis;links.new(projection,scale.inputs['Scale'])
        radial=vecnode('SUBTRACT',delta,scale.outputs[0]);unit=vecnode('NORMALIZE',radial)
        strip=mathnode('GREATER_THAN',vecnode('DOT_PRODUCT',unit,outward),.88)
        strip=mathnode('MULTIPLY',strip,mathnode('GREATER_THAN',projection,-.018))
        strip=mathnode('MULTIPLY',strip,mathnode('LESS_THAN',projection,(bone.tail_local-a).length+.015))
        strip=mathnode('MULTIPLY',strip,mathnode('GREATER_THAN',mathnode('MULTIPLY',x,sign),.17))
        mask_signal=mathnode('MAXIMUM',mask_signal,strip)
mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[1].default_value=(.027,.024,.021,1);mix.inputs[2].default_value=(.32,.135,.023,1)
links.new(mask_signal,mix.inputs[0]);links.new(mix.outputs[0],shader.inputs['Base Color'])
shader.inputs['Roughness'].default_value=.68
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=410;noise.inputs['Detail'].default_value=3
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.21;bump.inputs['Distance'].default_value=.0006
links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])

# Surface-derived pads/piping retain anatomical skin weights by nearest input
# vertex. Their geometry follows the actual cloth, not ellipsoid patches.
tree=KDTree(len(body.data.vertices))
for vertex in body.data.vertices:tree.insert(vertex.co,vertex.index)
tree.balance()
def weights(obj,role=None):
    cache={}
    for vertex in obj.data.vertices:
        if role:pairs=[(PREFIX+role,1)]
        else:
            p,index,d=tree.find(vertex.co)
            pairs=[(body.vertex_groups[g.group].name,g.weight) for g in body.data.vertices[index].groups if body.vertex_groups[g.group].name.startswith(PREFIX) and g.weight>.00001]
        total=sum(w for n,w in pairs)
        for name,weight in pairs:
            if name not in cache:cache[name]=obj.vertex_groups.new(name=name)
            cache[name].add([vertex.index],weight/total,'REPLACE')
    mod=obj.modifiers.new('Ash anatomical Generic deformation','ARMATURE');mod.object=rig
def mesh(name,vertices,faces,mat,role=None):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.parent=rig;data.materials.append(mat)
    for polygon in data.polygons:polygon.use_smooth=True
    active(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
    weights(obj,role);return obj
def tube(name,points,radius,mat,role=None,sides=6):
    vertices=[];faces=[]
    for i,p in enumerate(points):
        p=Vector(p);tangent=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).normalized()
        helper=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((1,0,0));a=tangent.cross(helper).normalized();b=tangent.cross(a).normalized()
        for j in range(sides):
            angle=math.tau*j/sides;vertices.append(p+radius*(a*math.cos(angle)+b*math.sin(angle)))
            if i:faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,vertices,faces,mat,role)
def project(point,offset=.002):
    hit,p,n,index=clothes.closest_point_on_mesh(point)
    if not hit:raise RuntimeError('Clothing projection failed')
    return p+n*offset
def pad(name,center,axis_u,axis_v,halfwidth,halfheight,mat):
    vertices=[];faces=[];rows=9;cols=9
    for i in range(rows):
        v=-1+2*i/(rows-1);width=halfwidth*(.80+.20*math.sqrt(max(0,1-v*v)))
        for j in range(cols):
            u=-1+2*j/(cols-1)
            dome=.0035*(1-u*u)*(1-v*v)
            vertices.append(project(center+axis_u*u*width+axis_v*v*halfheight,.003+dome))
            if i and j:
                k=i*cols+j;faces.append((k-cols-1,k-cols,k,k-1))
    obj=mesh(name,vertices,faces,mat)
    active(obj);solid=obj.modifiers.new('Protection panel thickness','SOLIDIFY');solid.thickness=.002
    bpy.ops.object.modifier_move_up(modifier=solid.name);bpy.ops.object.modifier_apply(modifier=solid.name)
    edge=list(vertices[:cols])+[vertices[i*cols+cols-1] for i in range(1,rows)]+list(reversed(vertices[-cols:-1]))+[vertices[i*cols] for i in range(rows-2,0,-1)]
    tube(name+'_Stitch',edge+[edge[0]],.0006,thread,sides=4)
    return obj
for side,sign in [('L',1),('R',-1)]:
    knee=rig.data.bones[PREFIX+'Shin_'+side].head_local
    center=knee+Vector((0,-.105,0))
    pad('AshV2_KneeProtection_'+side,center,Vector((1,0,0)),Vector((0,0,1)),.057,.075,black)
    for i in range(8):
        z=knee.z+.10+i*.010
        points=[project(Vector((knee.x-.058+j*.116/12,-.23,z)),.003+.0009*math.sin(j/12*math.pi)) for j in range(13)]
        tube('AshV2_KneeAccordion_'+side,points,.0023,black,sides=6)
    shoulder=rig.data.bones[PREFIX+'UpperArm_'+side].head_local
    axis=(rig.data.bones[PREFIX+'UpperArm_'+side].tail_local-shoulder).normalized()
    pad('AshV2_ShoulderProtection_'+side,shoulder+axis*.042+Vector((sign*.072,.008,.015)),Vector((0,1,0)),axis,.058,.067,black)
    elbow=rig.data.bones[PREFIX+'Forearm_'+side].head_local
    axis=(rig.data.bones[PREFIX+'Forearm_'+side].tail_local-elbow).normalized()
    pad('AshV2_ElbowProtection_'+side,elbow+Vector((sign*.051,.025,0)),Vector((0,1,0)),axis,.043,.07,black)
    ankle=rig.data.bones[PREFIX+'Foot_'+side].head_local
    for height in [.126,.202,.263]:
        vertices=[];faces=[];cols=48
        for i in range(cols):
            angle=math.tau*i/cols
            for j in range(2):vertices.append((ankle.x+.060*math.sin(angle),ankle.y-.006-.070*math.cos(angle),height+(j-.5)*(.016 if height<.26 else .023)))
            k=(i+1)%cols;faces.append((i*2,k*2,k*2+1,i*2+1))
        obj=mesh('AshV2_BootStrap_'+side,vertices,faces,brown,'Shin_'+side)
        active(obj);mod=obj.modifiers.new('Boot strap thickness','SOLIDIFY');mod.thickness=.003;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
        if height<.26:
            center=Vector((ankle.x+sign*.058,ankle.y-.004,height))
            corners=[center+Vector((0,-.014,-.010)),center+Vector((0,.014,-.010)),center+Vector((0,.014,.010)),center+Vector((0,-.014,.010))]
            tube('AshV2_BootBuckle_'+side,corners+[corners[0]],.002,metal,'Shin_'+side,6)
            tube('AshV2_BootBucklePin_'+side,[center+Vector((0,-.013,0)),center+Vector((0,.010,0))],.0011,metal,'Shin_'+side,6)

# Remove the rejected goggle strap section crossing in front of both lenses.
strap=bpy.data.objects['AshV2_GoggleLeatherStrap']
bm=bmesh.new();bm.from_mesh(strap.data)
remove=[f for f in bm.faces if f.calc_center_median().y<-.122 and abs(f.calc_center_median().x)<.087]
bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(strap.data);bm.free()
glass=bpy.data.materials['AshV2_AmberLens'];p=glass.node_tree.nodes['Principled BSDF']
p.inputs['Transmission Weight'].default_value=.82;p.inputs['Metallic'].default_value=0;p.inputs['Base Color'].default_value=(.30,.16,.045,1);p.inputs['Roughness'].default_value=.13

# Fit the chin strap around the jaw and close it beneath the chin.
for obj in list(scene.objects):
    if obj.name.startswith('AshV2_ChinStrap'):bpy.data.objects.remove(obj,do_unlink=True)
for side in [-1,1]:
    points=[Vector((side*.104,-.023,1.622)),Vector((side*.091,-.061,1.581)),Vector((side*.059,-.113,1.553)),Vector((0,-.125,1.549))]
    vertices=[];faces=[]
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();across=tangent.cross(Vector((0,-1,0))).normalized()*.006
        vertices.extend([p-across,p+across])
        if i:faces.append(((i-1)*2,(i-1)*2+1,i*2+1,i*2))
    obj=mesh('AshV2_ChinStrap_Fitted',vertices,faces,brown,'Head')
    active(obj);mod=obj.modifiers.new('Chin strap thickness','SOLIDIFY');mod.thickness=.0025;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)

bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print('ASH_V2_SURFACE_FIT_REFINED')
