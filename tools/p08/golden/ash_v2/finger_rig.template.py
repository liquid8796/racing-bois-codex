"""Add anatomical fingers while preserving every original semantic rig path.

Header J, BONE_NAMES and FINGER_DATA_JSON contain only licensed numeric asset
data. This is not an MPFB addon execution path.
"""
import bpy,bmesh,math,json
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];body=bpy.data.objects['AshV2_Body'];gloves=bpy.data.objects['AshV2_ArticulatedGloves'];PREFIX='RB_P06_Rider_L0_'
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
def cv(p):return Vector((p[0],-p[2],p[1]))
def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
active(rig);bpy.ops.object.mode_set(mode='EDIT')
for side in ['L','R']:
    for digit,label in [(1,'Thumb'),(2,'Index'),(3,'Middle'),(4,'Ring'),(5,'Pinky')]:
        for part in [1,2,3]:
            name=PREFIX+'Finger_'+label+'_'+str(part)+'_'+side
            bone=rig.data.edit_bones.new(name)
            bone.head=cv(J['joint-'+side.lower()+'-finger-'+str(digit)+'-'+str(part)])
            bone.tail=cv(J['joint-'+side.lower()+'-finger-'+str(digit)+'-'+str(part+1)])
            bone.parent=rig.data.edit_bones[PREFIX+('Hand_'+side if part==1 else 'Finger_'+label+'_'+str(part-1)+'_'+side)]
            bone.use_connect=part>1
bpy.ops.object.mode_set(mode='OBJECT')
numeric=json.loads(FINGER_DATA_JSON)
tree=KDTree(len(body.data.vertices))
for vertex in body.data.vertices:tree.insert(vertex.co,vertex.index)
tree.balance()
def set_weights(obj):
    obj.vertex_groups.clear();groups={}
    for vertex in obj.data.vertices:
        point,index,distance=tree.find(vertex.co)
        values=numeric.get(str(index))
        if not values:raise RuntimeError('No anatomical finger weights for '+str(index))
        values=sorted(values,key=weight_sort,reverse=True)[:4];total=sum(w for i,w in values)
        for i,weight in values:
            name=PREFIX+BONE_NAMES[i]
            if name not in groups:groups[name]=obj.vertex_groups.new(name=name)
            groups[name].add([vertex.index],weight/total,'REPLACE')
def weight_sort(pair):return pair[1]
set_weights(gloves)
black=bpy.data.materials['AshV2_CharcoalLeather']
def armor_patch(name,center,across,longitudinal,normal,width,height):
    vertices=[];faces=[];rows=5;columns=7
    for r in range(rows):
        v=-1+2*r/(rows-1)
        for c in range(columns):
            u=-1+2*c/(columns-1)
            point=center+across*u*width+longitudinal*v*height
            hit,position,surface_normal,index=gloves.closest_point_on_mesh(point)
            if not hit:raise RuntimeError('Glove armor projection missed')
            vertices.append(position+surface_normal*(.0017+.0015*(1-u*u)*(1-v*v)))
            if r and c:
                i=r*columns+c;faces.append((i-columns-1,i-columns,i,i-1))
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.parent=rig;data.materials.append(black)
    for face in data.polygons:face.use_smooth=True
    active(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
    set_weights(obj)
    modifier=obj.modifiers.new('Glove armor seam return','SOLIDIFY');modifier.thickness=.0015;bpy.ops.object.modifier_apply(modifier=modifier.name)
    modifier=obj.modifiers.new('Ash anatomical Generic deformation','ARMATURE');modifier.object=rig
for side,sign in [('L',1),('R',-1)]:
    lower=side.lower();wrist=cv(J['joint-'+lower+'-hand'])
    index=cv(J['joint-'+lower+'-finger-2-1']);middle=cv(J['joint-'+lower+'-finger-3-1']);pinky=cv(J['joint-'+lower+'-finger-5-1'])
    longitudinal=(middle-wrist).normalized();across=(index-pinky).normalized();normal=across.cross(longitudinal).normalized()
    if normal.x*sign<0:normal=-normal
    armor_patch('AshV2_GloveKnuckleArmor_'+side,(index+pinky)*.5-longitudinal*.015+normal*.018,across,longitudinal,normal,.029,.018)
    for digit,label in [(2,'Index'),(3,'Middle'),(4,'Ring'),(5,'Pinky')]:
        a=cv(J['joint-'+lower+'-finger-'+str(digit)+'-1']);b=cv(J['joint-'+lower+'-finger-'+str(digit)+'-2'])
        axis=(b-a).normalized()
        armor_patch('AshV2_GloveFingerArmor_'+label+'_'+side,(a+b)*.5+normal*.009,across,axis,normal,.0058,.010)
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print(json.dumps({'rig_bones':len(rig.data.bones),'original_semantic_paths_preserved':True,'finger_weights_bound':True}))
