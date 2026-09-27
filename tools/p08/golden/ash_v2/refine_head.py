"""Correct the first render's pointed brow opening and intersecting goggles."""
import bpy,math,json
from mathutils import Vector,Matrix
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig']
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
ivory=bpy.data.materials['AshV2_IvoryEnamel'];rubber=bpy.data.materials['AshV2_Rubber'];brown=bpy.data.materials['AshV2_BootLeather'];metal=bpy.data.materials['AshV2_AgedBrass'];black=bpy.data.materials['AshV2_CharcoalLeather']
def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
def mesh(name,vertices,faces,mat,uv=None,role='Head'):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.parent=rig
    data.materials.append(mat)
    for face in data.polygons:face.use_smooth=True
    if uv:
        layer=data.uv_layers.new(name='UV0')
        for loop in data.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
    else:
        active(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
    group=obj.vertex_groups.new(name='RB_P06_Rider_L0_'+role);group.add(list(range(len(data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Ash anatomical Generic deformation','ARMATURE');mod.object=rig
    return obj
def tube(name,points,radius,mat,sides=8,role='Head'):
    vertices=[];faces=[];uv=[]
    for i,p in enumerate(points):
        p=Vector(p);t=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).normalized()
        h=Vector((0,0,1)) if abs(t.z)<.9 else Vector((1,0,0));a=t.cross(h).normalized();b=t.cross(a).normalized()
        for j in range(sides):
            angle=math.tau*j/sides;vertices.append(p+radius*(a*math.cos(angle)+b*math.sin(angle)));uv.append((j/sides,i/len(points)))
            if i:faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,vertices,faces,mat,uv,role)
for obj in list(scene.objects):
    if obj.name.startswith(('AshV2_OpenFaceHelmetShell','AshV2_HelmetRubberReturn','AshV2_HelmetCheekPadding','AshV2_StandCollar','AshV2_CollarTopStitch')):bpy.data.objects.remove(obj,do_unlink=True)
rx=.112;ry=.128;cy=-.045;cz=1.704;rz=.147;rows=19;cols=64
def limit(phi):
    angle=abs((phi+math.pi)%math.tau-math.pi)
    t=max(0,min(1,(angle-.68)/.88));t=t*t*(3-2*t)
    return 1.19+.96*t
vertices=[];faces=[];uv=[]
for row in range(rows):
    v=.013+.987*row/(rows-1)
    for j in range(cols):
        phi=math.tau*j/cols;theta=limit(phi)*v
        vertices.append((rx*math.sin(theta)*math.sin(phi),cy-ry*math.sin(theta)*math.cos(phi),cz+rz*math.cos(theta)))
        uv.append((j/cols,v))
        if row:
            k=(j+1)%cols;faces.append(((row-1)*cols+j,(row-1)*cols+k,row*cols+k,row*cols+j))
faces.append(tuple(reversed(range(cols))))
obj=mesh('AshV2_OpenFaceHelmetShell',vertices,faces,ivory,uv)
active(obj);mod=obj.modifiers.new('Helmet wall thickness','SOLIDIFY');mod.thickness=.0065;mod.offset=-1;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
rim=vertices[-cols:]+[vertices[-cols]];tube('AshV2_HelmetRubberReturn',rim,.0046,rubber)
for side in [-1,1]:
    path=[]
    for i in range(18):
        phi=side*(.72+.65*i/17);theta=limit(phi)
        path.append((.104*math.sin(theta)*math.sin(phi),cy-.120*math.sin(theta)*math.cos(phi),cz+.141*math.cos(theta)))
    tube('AshV2_HelmetCheekPadding',path,.008,rubber,10)
# New goggle frame/lens pair wraps laterally around the helmet, while the
# missing front strap section leaves the amber glass unobstructed.
for obj in scene.objects:
    if obj.name.startswith(('AshV2_GoggleMetalFrame','AshV2_GoggleFoamGasket','AshV2_AmberGoggleLens')):
        center=sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices)
        side=1 if center.x>0 else -1
        for vertex in obj.data.vertices:
            vertex.co.y+=side*(vertex.co.x-center.x)*.45
            vertex.co.y-=.003

# Discrete enamel chips/roughness, generated in the source shader and later
# baked to actual PBR maps. This does not substitute for concept comparison.
nodes=ivory.node_tree.nodes;links=ivory.node_tree.links;p=nodes['Principled BSDF']
vor=nodes.new('ShaderNodeTexVoronoi');vor.distance='EUCLIDEAN';vor.inputs['Scale'].default_value=29
compare=nodes.new('ShaderNodeMath');compare.operation='LESS_THAN';compare.inputs[1].default_value=.057;links.new(vor.outputs['Distance'],compare.inputs[0])
mix=nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.57,.52,.42,1);mix.inputs[2].default_value=(.12,.071,.03,1)
links.new(compare.outputs[0],mix.inputs[0]);links.new(mix.outputs[0],p.inputs['Base Color'])
rough=nodes.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1;rough.inputs['To Min'].default_value=.37;rough.inputs['To Max'].default_value=.70
links.new(compare.outputs[0],rough.inputs['Value']);links.new(rough.outputs[0],p.inputs['Roughness'])

# Proper collar follows the imported shirt neck opening above its crew edge.
rows=3;cols=48;vertices=[];faces=[];uv=[]
for i in range(rows):
    for j in range(cols):
        a=.17+(math.tau-.34)*j/(cols-1)
        vertices.append(((.074-i*.002)*math.sin(a),-.011-(.079-i*.003)*math.cos(a),1.535+i*.017))
        uv.append((j/(cols-1),i/2))
        if i and j:
            k=i*cols+j;faces.append((k-cols-1,k-cols,k,k-1))
collar=mesh('AshV2_StandCollar',vertices,faces,black,uv,'Torso')
active(collar);mod=collar.modifiers.new('Collar leather thickness','SOLIDIFY');mod.thickness=.003;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
tube('AshV2_CollarTopStitch',vertices[-cols:],.0006,bpy.data.materials['AshV2_OchreThread'],4,'Torso')

# Hold all expression keys neutral during model/skin verification.
body=bpy.data.objects['AshV2_Body']
if body.data.shape_keys:
    for key in body.data.shape_keys.key_blocks:key.value=0
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print('ASH_V2_HEAD_EQUIPMENT_REFINED')
