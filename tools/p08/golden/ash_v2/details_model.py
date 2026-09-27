"""Concept-specific Ash garments and equipment on the anatomical foundation.

All operations run in the direct safe-mode Blender MCP. Garment panels derive
from continuous fitted clothing surfaces; hands retain anatomical finger mesh.
The authored candidate remains subject to actual render/concept acceptance.
"""
import bpy,bmesh,math,json
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT='D:/Project/Unity/racing-bois/'
SOURCE=ROOT+'ArtSource/P08/Golden/Ash/V2/'
scene=bpy.context.scene
rig=bpy.data.objects['RB_P06_Rider_Rig']
body=bpy.data.objects['AshV2_Body']
clothes=bpy.data.objects['AshV2_Clothes']
PREFIX='RB_P06_Rider_L0_'
def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
def surface_material(name,color,roughness,metallic=0,grain=.15):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic
    if grain:
        tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=260;tex.inputs['Detail'].default_value=3;tex.inputs['Roughness'].default_value=.72
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=grain;bump.inputs['Distance'].default_value=.0005
        links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
        mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.11;mix.inputs[1].default_value=(*color,1)
        links.new(tex.outputs['Fac'],mix.inputs[2]);links.new(mix.outputs[0],p.inputs['Base Color'])
    return mat
black=bpy.data.materials['AshV2_CharcoalLeather'];brown=bpy.data.materials['AshV2_BootLeather']
amber=surface_material('AshV2_OchreLeather',(.37,.185,.047),.58,grain=.18)
rubber=surface_material('AshV2_Rubber',(.014,.012,.010),.76,grain=.20)
metal=surface_material('AshV2_AgedBrass',(.27,.19,.095),.37,.78,.04)
ivory=surface_material('AshV2_IvoryEnamel',(.74,.685,.56),.34,.10,.015)
ivory.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.28
lens=surface_material('AshV2_AmberLens',(.23,.11,.021),.16,.12,0)
lens.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=.25
lens.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.65
stitch=surface_material('AshV2_OchreThread',(.205,.143,.068),.83,grain=0)
tree=KDTree(len(body.data.vertices))
for vertex in body.data.vertices:tree.insert(vertex.co,vertex.index)
tree.balance()
def assign_weights(obj,role=None):
    cache={}
    for vertex in obj.data.vertices:
        if role:weights=[(PREFIX+role,1)]
        else:
            point,index,distance=tree.find(vertex.co)
            weights=[(body.vertex_groups[g.group].name,g.weight) for g in body.data.vertices[index].groups if g.weight>.00001]
        total=sum(w for n,w in weights)
        if not total:raise RuntimeError('New detail has no anatomical weights')
        for name,weight in weights:
            if name not in cache:
                cache[name]=obj.vertex_groups.get(name)
                if cache[name] is None:cache[name]=obj.vertex_groups.new(name=name)
            cache[name].add([vertex.index],weight/total,'REPLACE')
    modifier=obj.modifiers.new('Ash anatomical Generic deformation','ARMATURE');modifier.object=rig
def unwrap(obj):
    active(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.012,area_weight=.5)
    bpy.ops.object.mode_set(mode='OBJECT')
def mesh(name,vertices,faces,mat,role=None,uv=None,smooth=True):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.parent=rig
    data.materials.append(mat)
    for polygon in data.polygons:polygon.use_smooth=smooth
    if uv:
        layer=data.uv_layers.new(name='UV0')
        for loop in data.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
    else:unwrap(obj)
    assign_weights(obj,role)
    return obj
def tube(name,points,radius,mat,role=None,sides=6):
    vertices=[];faces=[];uv=[];length=0
    for i,p in enumerate(points):
        p=Vector(p)
        if i:length+=(p-Vector(points[i-1])).length
        tangent=(Vector(points[min(len(points)-1,i+1)])-Vector(points[max(0,i-1)])).normalized()
        up=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((1,0,0))
        a=tangent.cross(up).normalized();b=tangent.cross(a).normalized()
        for j in range(sides):
            angle=math.tau*j/sides;vertices.append(p+radius*(a*math.cos(angle)+b*math.sin(angle)));uv.append((j/sides,length*5))
            if i:faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,vertices,faces,mat,role,uv)
def box(name,center,size,mat,role=None,bevel=.001):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);obj=bpy.context.object;obj.name=name;obj.dimensions=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    if bevel:
        mod=obj.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel;mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.materials.clear();obj.data.materials.append(mat);obj.parent=rig;unwrap(obj);assign_weights(obj,role)
    return obj
def point_front(x,z,offset=.001):
    hit,location,normal,index=clothes.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))
    if not hit:return None
    return location+normal*offset
def path_front(points,offset=.001):
    out=[]
    for x,z in points:
        point=point_front(x,z,offset)
        if point is not None:out.append(point)
    return out

# One subdivision gives the continuous garment enough topology for panel
# boundaries and deformation. Its original cloth UVs and anatomical weights
# are retained; no floating cylindrical sleeves are introduced.
active(clothes)
bpy.ops.object.modifier_apply(modifier='Sculpt surface subdivision')
clothes.data.materials.append(amber);clothes.data.materials.append(rubber)
for polygon in clothes.data.polygons:
    p=polygon.center;x,y,z=p
    band=False
    if y<-.055 and .055<abs(x)<.265:
        line=1.435+.22*(abs(x)-.10)
        band=line-.022<z<line+.007
    if y>.004 and abs(x)<.255 and 1.433<z<1.464:band=True
    for side,sign in [('L',1),('R',-1)]:
        if x*sign<.19:continue
        for name in ['UpperArm_'+side,'Forearm_'+side]:
            bone=rig.data.bones[PREFIX+name];a=bone.head_local;b=bone.tail_local
            axis=(b-a).normalized();t=max(0,min((p-a).dot(axis),(b-a).length))
            radial=p-a-axis*t
            outward=Vector((sign,0,0));outward=(outward-axis*outward.dot(axis)).normalized()
            if radial.length>.01 and radial.normalized().dot(outward)>.88:band=True
    if band:polygon.material_index=1
    if z<.99:polygon.material_index=2
# Add realistic leather thickness with real open cuffs/neck/hem returns.
active(clothes)
thick=clothes.modifiers.new('Sewn leather shell thickness','SOLIDIFY');thick.thickness=.0028;thick.offset=1
bpy.ops.object.modifier_move_up(modifier=thick.name)
bpy.ops.object.modifier_apply(modifier=thick.name)

# Articulated leather gloves derive from the anatomical hand surface, including
# all fingers and thumbs. A normal offset adds garment ease without joint balls.
gloves=body.copy();gloves.data=body.data.copy();scene.collection.objects.link(gloves);gloves.name='AshV2_ArticulatedGloves';gloves.shape_key_clear()
for mod in list(gloves.modifiers):gloves.modifiers.remove(mod)
bm=bmesh.new();bm.from_mesh(gloves.data)
deform=bm.verts.layers.deform.verify();hand_groups={g.index for g in gloves.vertex_groups if g.name.endswith(('Hand_L','Hand_R'))}
remove=[]
for face in bm.faces:
    score=sum(sum(v[deform].get(i,0) for i in hand_groups) for v in face.verts)/len(face.verts)
    if score<.58:remove.append(face)
bmesh.ops.delete(bm,geom=remove,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
for vertex in bm.verts:vertex.co+=vertex.normal*.0018
bm.to_mesh(gloves.data);bm.free()
gloves.data.materials.clear();gloves.data.materials.append(black)
for polygon in gloves.data.polygons:polygon.material_index=0;polygon.use_smooth=True
modifier=gloves.modifiers.new('Glove leather surface','SUBSURF');modifier.levels=1;modifier.render_levels=1
modifier=gloves.modifiers.new('Glove seam returns','SOLIDIFY');modifier.thickness=.0012
modifier=gloves.modifiers.new('Ash anatomical Generic deformation','ARMATURE');modifier.object=rig

# Jacket zipper and paired pocket zips follow ray-projected garment surfaces.
zip_points=path_front([(0,1.026+i*.008) for i in range(61)],.0034)
tube('AshV2_CenterZipTape',zip_points,.0036,rubber)
for i,point in enumerate(zip_points):
    for side in [-1,1]:box('AshV2_ZipTooth',point+Vector((side*.0022,-.0006,0)),(.0036,.0018,.0026),metal,bevel=.0004)
for side in [-1,1]:
    seam=path_front([(side*.009,1.028+i*.011) for i in range(45)],.0032)
    tube('AshV2_ZipStitch',seam,.00055,stitch,sides=4)
    pocket=path_front([(side*(.111+.038*t),1.135+.142*t) for t in [i/22 for i in range(23)]],.0032)
    tube('AshV2_PocketZipTape',pocket,.003,rubber)
    tube('AshV2_PocketZipTeeth',pocket,.0013,metal,sides=5)
    if pocket:box('AshV2_PocketPull',pocket[0]+Vector((0,-.002,-.006)),(.009,.003,.018),metal,bevel=.001)
    side_seam=path_front([(side*(.125+.014*math.sin(t*math.pi)),1.045+.322*t) for t in [i/30 for i in range(31)]],.0023)
    tube('AshV2_TailoredChestSeam',side_seam,.00065,stitch,sides=4)
if zip_points:box('AshV2_MainZipPull',zip_points[-1]+Vector((0,-.003,-.011)),(.012,.005,.023),metal,bevel=.0015)

# Stand collar: a sewn oval ring around the actual neck, with a small frontal
# opening for the zipper and a doubled upper edge rather than a capped tube.
verts=[];faces=[];uv=[];columns=48
for row in range(3):
    z=1.502+row*.020
    for j in range(columns):
        a=.16+(math.tau-.32)*j/(columns-1)
        rx=.076-row*.001;ry=.072-row*.001
        verts.append((rx*math.sin(a),-.012-ry*math.cos(a),z))
        uv.append((j/(columns-1),row*.5))
        if row and j:faces.append(((row-1)*columns+j-1,(row-1)*columns+j,row*columns+j,row*columns+j-1))
collar=mesh('AshV2_StandCollar',verts,faces,black,uv=uv)
active(collar);mod=collar.modifiers.new('Collar sewn thickness','SOLIDIFY');mod.thickness=.003;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
tube('AshV2_CollarTopStitch',verts[-columns:],.00065,stitch,sides=4)

# Open-face helmet: an authored wraparound shell with a brow opening, lower
# ear protection and continuous gasket. This is not a complete sphere hiding
# the face, and its inner return is real geometry.
rx=.112;ry=.128;cz=1.704;cy=-.045;rz=.147;rows=17;columns=64
vertices=[];faces=[];uv=[]
def helmet_limit(phi):
    angle=abs((phi+math.pi)%math.tau-math.pi)
    t=max(0,min(1,angle/(math.pi*.55)));t=t*t*(3-2*t)
    return 1.12+1.03*t
for row in range(rows):
    fraction=.018+.982*row/(rows-1)
    for j in range(columns):
        phi=math.tau*j/columns;theta=helmet_limit(phi)*fraction
        vertices.append((rx*math.sin(theta)*math.sin(phi),cy-ry*math.sin(theta)*math.cos(phi),cz+rz*math.cos(theta)))
        uv.append((j/columns,fraction))
        if row:
            k=(j+1)%columns;faces.append(((row-1)*columns+j,(row-1)*columns+k,row*columns+k,row*columns+j))
faces.append(tuple(reversed(range(columns))))
helmet=mesh('AshV2_OpenFaceHelmetShell',vertices,faces,ivory,'Head',uv)
active(helmet);mod=helmet.modifiers.new('Enamel composite shell thickness','SOLIDIFY');mod.thickness=.007;mod.offset=-1
bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
rim=vertices[-columns:]+[vertices[-columns]]
tube('AshV2_HelmetRubberReturn',rim,.0048,rubber,'Head',8)

# Padded helmet inner cheek edges conform to the shell rather than floating
# beside the face. Side fasteners use a small beveled head at real shell points.
for side in [-1,1]:
    path=[]
    for i in range(13):
        t=i/12;phi=side*(.90+.43*t);theta=1.22+.78*t
        path.append((.104*math.sin(theta)*math.sin(phi),cy-.121*math.sin(theta)*math.cos(phi),cz+.139*math.cos(theta)))
    tube('AshV2_HelmetCheekPadding',path,.009,rubber,'Head',10)
    for z,y in [(1.734,-.064),(1.682,-.058),(1.642,-.024)]:
        box('AshV2_HelmetRivet',(side*.111,y,z),(.004,.009,.009),metal,'Head',.002)
    strap=[(side*.104,-.023,1.622),(side*.092,-.051,1.588),(side*.073,-.077,1.555),(side*.025,-.084,1.542)]
    # Flat ribbon with a shaped inner/outer loop gives the leather strap width.
    verts=[]
    for p in strap:
        verts.extend([(p[0],p[1]-.004,p[2]-.006),(p[0],p[1]+.004,p[2]+.006)])
    faces=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(strap)-1)]
    band=mesh('AshV2_ChinStrap',verts,faces,brown,'Head')
    active(band);mod=band.modifiers.new('Chin leather thickness','SOLIDIFY');mod.thickness=.003;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
    if side<0:box('AshV2_ChinStrapBuckle',(side*.080,-.073,1.566),(.016,.010,.022),metal,'Head',.003)

# Goggles strap follows the outside of the helmet crown. Original Ash uses
# paired rounded rectangular amber lenses, metal frames and a leather bridge.
verts=[];faces=[];uv=[];n=96
for i in range(n):
    a=i*math.tau/n
    for j in range(2):
        verts.append((.114*math.sin(a),cy-.129*math.cos(a),1.752+.042*math.cos(a)+(j-.5)*.025))
        uv.append((i/n,j))
    nxt=(i+1)%n;faces.append((i*2,nxt*2,nxt*2+1,i*2+1))
strap=mesh('AshV2_GoggleLeatherStrap',verts,faces,brown,'Head',uv)
active(strap);mod=strap.modifiers.new('Goggle strap leather thickness','SOLIDIFY');mod.thickness=.0025;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
def rounded_rectangle(width,height,radius,steps=5):
    points=[]
    for cx,cy2,start in [(width/2-radius,height/2-radius,0),(-width/2+radius,height/2-radius,90),(-width/2+radius,-height/2+radius,180),(width/2-radius,-height/2+radius,270)]:
        for i in range(steps):
            a=math.radians(start+i*90/(steps-1));points.append((cx+radius*math.cos(a),cy2+radius*math.sin(a)))
    return points
for side in [-1,1]:
    center=Vector((side*.048,-.153,1.786));horizontal=Vector((1,0,0));vertical=Vector((0,.37,.929))
    outline=rounded_rectangle(.087,.052,.013)
    frame=[center+horizontal*x+vertical*y for x,y in outline]
    tube('AshV2_GoggleMetalFrame',frame+[frame[0]],.0035,metal,'Head',8)
    gasket=[p+Vector((0,.004,0)) for p in frame]
    tube('AshV2_GoggleFoamGasket',gasket+[gasket[0]],.0046,rubber,'Head',8)
    glass=[center+horizontal*(x*.91)+vertical*(y*.87)+Vector((0,-.001,0)) for x,y in outline]
    obj=mesh('AshV2_AmberGoggleLens',glass,[tuple(range(len(glass)))],lens,'Head',smooth=False)
    active(obj);mod=obj.modifiers.new('Lens physical thickness','SOLIDIFY');mod.thickness=.002;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
tube('AshV2_GoggleNoseBridge',[(-.010,-.155,1.788),(0,-.160,1.779),(.010,-.155,1.788)],.006,brown,'Head',8)

# Keep the source editable and the original anatomical input before any LOD
# or export operation. Structural/visual acceptance is intentionally pending.
bpy.ops.wm.save_as_mainfile(filepath=SOURCE+'RB_Golden_Ash_V2.blend')
print(json.dumps({'details':'authored','objects':len(scene.objects),'rigBones':len(rig.data.bones),'productionAccepted':False}))
