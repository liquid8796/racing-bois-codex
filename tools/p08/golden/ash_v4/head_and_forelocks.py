import bpy,math,json
from mathutils import Vector,Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];m=obj.data
    assert not obj.get('v4_face_sculpt',False)
    ids=set(i for p in m.polygons if m.materials[p.material_index].name=='AshV2_Skin_Baked' for i in p.vertices)
    maximum=0;count=0
    for i in ids:
        p=m.vertices[i].co.copy();x,y,z=p
        if y>-.07 or not 1.572<z<1.731 or abs(x)>.09:continue
        front=max(0,min(1,(-y-.07)/.04));delta=Vector()
        nose=math.exp(-(x/.017)**2-((z-1.657)/.028)**2)
        brow=math.exp(-((abs(x)-.035)/.021)**2-((z-1.704)/.010)**2)
        cheek=math.exp(-((abs(x)-.060)/.022)**2-((z-1.670)/.021)**2)
        hollow=math.exp(-((abs(x)-.052)/.025)**2-((z-1.627)/.017)**2)
        chin=math.exp(-(x/.036)**2-((z-1.591)/.013)**2)
        delta.y=(-.0045*nose-.0018*brow-.0012*cheek+.0028*hollow-.0028*chin)*front
        delta.x=((1 if x>0 else -1)*.0022*cheek-x*.055*chin)*front
        if delta.length:
            saved=[key.data[i].co.copy() for key in m.shape_keys.key_blocks]
            m.vertices[i].co=p+delta
            for key,co in zip(m.shape_keys.key_blocks,saved):key.data[i].co=co+delta
            maximum=max(maximum,delta.length);count+=1
    m.update()
    for v in m.vertices:m.attributes['AshV4_RestMeters'].data[v.index].vector=v.co
    obj['v4_face_sculpt']=True;rows.append({'lod':level,'vertices':count,'maximumDeltaMetres':maximum})

skin=bpy.data.materials['AshV2_Skin_Baked'].copy();skin.name='AshV4_Skin_Source'
nodes=skin.node_tree.nodes;links=skin.node_tree.links;bs=nodes['Principled BSDF']
original=bs.inputs['Base Color'].links[0].from_socket
tone=nodes.new('ShaderNodeMixRGB');tone.blend_type='MULTIPLY';tone.inputs[0].default_value=1;tone.inputs[2].default_value=(.74,.68,.61,1)
links.new(original,tone.inputs[1]);links.new(tone.outputs[0],bs.inputs['Base Color'])
attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='AshV4_RestMeters'
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1600;noise.inputs['Detail'].default_value=2
links.new(attr.outputs['Vector'],noise.inputs['Vector'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.00015
if bs.inputs['Normal'].is_linked:links.new(bs.inputs['Normal'].links[0].from_socket,bump.inputs['Normal'])
links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
for link in list(bs.inputs['Roughness'].links):links.remove(link)
bs.inputs['Roughness'].default_value=.57;skin['ash_v4_source_role']='Skin';skin['texture_size']=2048
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin']
    for i,m in enumerate(obj.data.materials):
        if m.name=='AshV2_Skin_Baked':obj.data.materials[i]=skin

hair=bpy.data.materials.new('AshV4_Forelock_Source');hair.use_nodes=True
nodes=hair.node_tree.nodes;links=hair.node_tree.links;bs=nodes['Principled BSDF']
tex=nodes.new('ShaderNodeTexCoord');wave=nodes.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='X';wave.inputs['Scale'].default_value=24;wave.inputs['Distortion'].default_value=.18
links.new(tex.outputs['UV'],wave.inputs['Vector'])
color=nodes.new('ShaderNodeMixRGB');color.inputs[1].default_value=(.009,.006,.004,1);color.inputs[2].default_value=(.036,.022,.014,1)
links.new(wave.outputs['Fac'],color.inputs[0]);links.new(color.outputs[0],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.49
hair['ash_v4_source_role']='Forelocks';hair['texture_size']=512
collection=bpy.data.collections.new('AshV4_HairDetails_Source');bpy.context.scene.collection.children.link(collection)
# Authored curved hair clumps rooted under the helmet and tapering onto the
# forehead/temples. Real ribbon curvature forms the silhouette; no helmet-cap
# primitive, face photograph, or camera-facing concept texture is used.
paths=[
 ((.057,-.121,1.783),(.078,-.154,1.759),(.046,-.171,1.750),(.014,-.164,1.723),.007),
 ((.028,-.117,1.788),(.045,-.159,1.769),(.005,-.173,1.751),(-.029,-.159,1.725),.008),
 ((-.005,-.112,1.791),(-.014,-.160,1.772),(-.051,-.171,1.749),(-.068,-.147,1.711),.007),
 ((-.042,-.106,1.786),(-.066,-.144,1.765),(-.070,-.164,1.739),(-.080,-.134,1.699),.006),
 ((.070,-.088,1.766),(.091,-.123,1.743),(.091,-.140,1.716),(.084,-.117,1.692),.006),
 ((-.070,-.090,1.760),(-.097,-.122,1.732),(-.092,-.136,1.707),(-.085,-.112,1.678),.006),
 ((.043,-.118,1.782),(.063,-.164,1.761),(.011,-.177,1.750),(-.011,-.165,1.733),.0045),
 ((-.020,-.107,1.792),(-.019,-.162,1.774),(-.054,-.172,1.759),(-.057,-.157,1.731),.0045)]
created=[]
for index,(a,b,c,d,width) in enumerate(paths):
    a,b,c,d=Vector(a),Vector(b),Vector(c),Vector(d);vertices=[];faces=[];uv=[];segments=18;columns=5
    for i in range(segments+1):
        t=i/segments;position=(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
        tangent=(3*(1-t)**2*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c)).normalized()
        front=Vector((0,-1,0));across=tangent.cross(front).normalized();normal=across.cross(tangent).normalized()
        halfwidth=width*(.52+.48*math.sin(t*math.pi))*(1-.94*t*t)
        for j in range(columns):
            u=-1+2*j/(columns-1);point=position+across*halfwidth*u+normal*.0012*(1-u*u)*math.sin(math.pi*t)
            vertices.append(point);uv.append((j/(columns-1),t))
            if i and j:
                k=i*columns+j;faces.append((k-columns-1,k-columns,k,k-1))
    data=bpy.data.meshes.new('AshV4_Forelock_%02d'%index);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(data.name,data);collection.objects.link(obj);obj.parent=rig;data.materials.append(hair)
    layer=data.uv_layers.new(name='UV0')
    for loop in data.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
    for face in data.polygons:face.use_smooth=True
    attr=data.attributes.new('AshV4_RestMeters','FLOAT_VECTOR','POINT')
    for v in data.vertices:attr.data[v.index].vector=v.co
    group=obj.vertex_groups.new(name='RB_P06_Rider_L0_Head');group.add(list(range(len(vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Preserved Ash head deformation','ARMATURE');mod.object=rig
    obj['v4_hair_detail']=True;created.append(obj)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_HEAD '+json.dumps({'faceSculpt':rows,'hairClumps':len(created),'hairVertices':sum(len(o.data.vertices) for o in created),'newSkinRequiresBake':True,'fidelityAccepted':False}))
