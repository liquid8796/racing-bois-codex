import bpy,math,json
from array import array
from mathutils import Vector
SOURCE='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_PreEdit.blend'
DESTINATION='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_Jacket01.blend'
if bpy.data.filepath.replace('\\','/')!=SOURCE or bpy.context.scene.get('ash_v8_jacket01_authored'):
    raise RuntimeError('Fresh owned pre-edit scene required')
if bpy.context.preferences.filepaths.use_scripts_auto_execute:raise RuntimeError('Auto-execute must remain off')
rig=bpy.data.objects['RB_P06_Rider_Rig']
def curves(action):
    rows=[]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    rows.append((curve.data_path,curve.array_index,curve.extrapolation,[(tuple(p.co),tuple(p.handle_left),tuple(p.handle_right),p.interpolation,p.handle_left_type,p.handle_right_type) for p in curve.keyframe_points]))
    return rows
actions_before={action.name:curves(action) for action in bpy.data.actions}
bones_before=[(bone.name,bone.parent.name if bone.parent else '',tuple(tuple(row) for row in bone.matrix_local)) for bone in rig.data.bones]
def values(collection,property_name,count,kind='f'):
    result=array(kind,[0])*count;collection.foreach_get(property_name,result);return result
def smooth(a,b,value):
    t=max(0,min(1,(value-a)/(b-a)));return t*t*(3-2*t)
def gauss(value,width):return math.exp(-(value/width)**2)
def segment(point,a,b):
    axis=b-a;t=max(0,min(1,(point-a).dot(axis)/axis.length_squared));center=a+t*axis
    return (point-center).length,t,center
def displacement(point,bone_name):
    if bone_name.endswith('_Torso') or bone_name.endswith('_Hip'):
        gate=smooth(1.045,1.10,point.z)*(1-smooth(1.35,1.46,point.z))
        y=.026-(point.z-1.072)*.084
        radial=Vector((point.x/.19**2,(point.y-y)/.13**2,0))
        if not radial.length or not gate:return Vector((0,0,0))
        radial.normalize();side=smooth(.025,.16,abs(point.x))
        phase=(point.z-1.13+.22*abs(point.x)+.012*math.sin(point.x*24))/ .041
        waist=.0045*gauss(point.z-1.15,.078)*(.20+.80*side)*(.5+.5*math.sin(math.tau*phase))**2
        chest=.0026*gauss(point.z-(1.31-.20*abs(point.x)),.048)*side*(.5+.5*math.sin(math.tau*(point.z+.30*abs(point.x))/.063))**2
        return radial*((waist+chest)*gate)
    if not ('UpperArm_' in bone_name or 'Forearm_' in bone_name):return Vector((0,0,0))
    side=bone_name[-1]
    upper=rig.data.bones['RB_P06_Rider_L0_UpperArm_'+side];fore=rig.data.bones['RB_P06_Rider_L0_Forearm_'+side]
    du,tu,cu=segment(point,upper.head_local,upper.tail_local);df,tf,cf=segment(point,fore.head_local,fore.tail_local)
    if du<df:s=tu*upper.length;center=cu
    else:s=upper.length+tf*fore.length;center=cf
    radial=point-center
    if not radial.length:return Vector((0,0,0))
    radial.normalize();inside=((fore.tail_local-fore.head_local).normalized()-(upper.tail_local-upper.head_local).normalized()).normalized()
    compression=.25+.75*max(0,radial.dot(inside))
    theta=math.atan2(radial.y,radial.x*(1 if side=='L' else -1))
    gate=smooth(.09,.16,s)*(1-smooth(upper.length+fore.length-.06,upper.length+fore.length-.025,s))
    phase=math.tau*(s-upper.length)/.031+.65*math.sin(theta*2+.4)
    elbow=.0062*gauss(s-upper.length,.059)*compression*(.5+.5*math.sin(phase))**2
    cuff=.0026*gauss(s-(upper.length+fore.length-.072),.034)*(.55+.45*math.sin(theta+1.1)**2)*(.5+.5*math.sin(math.tau*s/.022+theta))**2
    return radial*((elbow+cuff)*gate)

material_changes=[];copies={}
for name,value,saturation,rough_scale,grain in [
    ('AshV4_TailoredLeather_Baked',.50,1.28,.82,True),
    ('AshV4_LeatherDetails_Baked',.57,1.18,.88,True),
    ('AshV2_OchreThread_Baked',.62,1.10,1.0,False)]:
    original=bpy.data.materials[name];copy=original.copy();copy.name='AshV8_'+name+'_JacketStudy'
    nodes=copy.node_tree.nodes;links=copy.node_tree.links;shader=next(node for node in nodes if node.type=='BSDF_PRINCIPLED')
    color_link=next(link for link in links if link.to_socket==shader.inputs['Base Color']);color_source=color_link.from_socket
    links.remove(color_link);tone=nodes.new('ShaderNodeHueSaturation');tone.name='AshV8_CharcoalAmberTone'
    tone.inputs['Value'].default_value=value;tone.inputs['Saturation'].default_value=saturation
    links.new(color_source,tone.inputs['Color']);links.new(tone.outputs['Color'],shader.inputs['Base Color'])
    if rough_scale!=1:
        rough_link=next(link for link in links if link.to_socket==shader.inputs['Roughness']);rough_source=rough_link.from_socket
        links.remove(rough_link);scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.use_clamp=True;scale.inputs[1].default_value=rough_scale
        links.new(rough_source,scale.inputs[0]);links.new(scale.outputs[0],shader.inputs['Roughness'])
    if grain:
        normal_link=next(link for link in links if link.to_socket==shader.inputs['Normal']);normal_source=normal_link.from_socket;links.remove(normal_link)
        coordinates=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=220;noise.inputs['Detail'].default_value=2
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.00035
        links.new(coordinates.outputs['Object'],noise.inputs['Vector']);links.new(noise.outputs['Fac'],bump.inputs['Height'])
        links.new(normal_source,bump.inputs['Normal']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
        shader.inputs['Coat Weight'].default_value=.10;shader.inputs['Coat Roughness'].default_value=.32
    copies[name]=copy;material_changes.append(dict(source=name,candidate=copy.name,value=value,saturation=saturation,roughnessMultiplier=rough_scale,microBumpMetres=.00035 if grain else 0))

rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];mesh=obj.data
    if mesh.users!=1 or mesh.library or obj.library:raise RuntimeError('Independently owned local LOD mesh required')
    positions=values(mesh.vertices,'co',len(mesh.vertices)*3);loops=values(mesh.loops,'vertex_index',len(mesh.loops),'i')
    uv_before=[values(layer.data,'uv',len(mesh.loops)*2) for layer in mesh.uv_layers]
    weights_before=[tuple((group.group,group.weight) for group in vertex.groups) for vertex in mesh.vertices]
    keys=mesh.shape_keys.key_blocks if mesh.shape_keys else []
    morph_before=[]
    if keys:
        basis=values(keys[0].data,'co',len(mesh.vertices)*3)
        for key in keys[1:]:
            coords=values(key.data,'co',len(mesh.vertices)*3);morph_before.append(array('f',(value-base for value,base in zip(coords,basis))))
    roles=[set() for vertex in mesh.vertices]
    for polygon in mesh.polygons:
        for index in polygon.vertices:roles[index].add(polygon.material_index)
    changed=[];maximum=0
    for vertex in mesh.vertices:
        if not roles[vertex.index] or not roles[vertex.index].issubset({1,2,6,7}):continue
        dominant=max(((group.weight,group.group) for group in vertex.groups),default=(0,-1))
        if dominant[1]<0:continue
        bone=obj.vertex_groups[dominant[1]].name
        point=Vector(positions[vertex.index*3:vertex.index*3+3]);delta=displacement(point,bone)
        if delta.length<1e-7:continue
        if delta.length>.008:raise RuntimeError('Eight-millimetre garment displacement bound exceeded')
        if keys and any(tuple(key.data[vertex.index].co)!=tuple(keys[0].data[vertex.index].co) for key in keys[1:]):
            raise RuntimeError('Refuse to change a vertex with an authored nonzero expression delta')
        destination=point+delta
        for key in keys:key.data[vertex.index].co=destination
        vertex.co=destination;changed.append(vertex.index);maximum=max(maximum,delta.length)
    for index,material in enumerate(mesh.materials):
        if material.name in copies:mesh.materials[index]=copies[material.name]
    mesh.update();mesh.calc_loop_triangles()
    if loops!=values(mesh.loops,'vertex_index',len(mesh.loops),'i'):raise RuntimeError('Topology changed')
    if uv_before!=[values(layer.data,'uv',len(mesh.loops)*2) for layer in mesh.uv_layers]:raise RuntimeError('UVs changed')
    if weights_before!=[tuple((group.group,group.weight) for group in vertex.groups) for vertex in mesh.vertices]:raise RuntimeError('Weights changed')
    if keys:
        basis=values(keys[0].data,'co',len(mesh.vertices)*3);morph_after=[]
        for key in keys[1:]:
            coords=values(key.data,'co',len(mesh.vertices)*3);morph_after.append(array('f',(value-base for value,base in zip(coords,basis))))
        if morph_before!=morph_after:raise RuntimeError('Expression deltas changed')
    changed_set=set(changed)
    if any(tuple(vertex.co)!=tuple(positions[vertex.index*3:vertex.index*3+3]) for vertex in mesh.vertices if vertex.index not in changed_set):
        raise RuntimeError('Untouched vertex changed')
    bad=0;minimum=None
    for triangle in mesh.loop_triangles:
        a,b,c=[mesh.vertices[index].co for index in triangle.vertices];cross=(b-a).cross(c-a).length_squared
        if not math.isfinite(cross) or cross<=1e-16:bad+=1
        minimum=cross if minimum is None else min(minimum,cross)
    if bad:raise RuntimeError('Physical triangle threshold failed after garment shaping')
    rows.append(dict(lod=level,changedVertices=len(changed),maximumDisplacementMetres=maximum,vertices=len(mesh.vertices),triangles=len(mesh.loop_triangles),
        minimumPhysicalCrossSquared=minimum,topologyExact=True,uvExact=True,weightsExact=True,expressionDeltasExact=True,untouchedVerticesExact=True))
if actions_before!={action.name:curves(action) for action in bpy.data.actions}:raise RuntimeError('Action changed')
if bones_before!=[(bone.name,bone.parent.name if bone.parent else '',tuple(tuple(row) for row in bone.matrix_local)) for bone in rig.data.bones]:raise RuntimeError('Rest rig changed')
bpy.context.scene['ash_v8_jacket01_authored']=True
bpy.ops.wm.save_as_mainfile(filepath=DESTINATION,compress=True)
print('ASH_V8_JACKET01 '+json.dumps(dict(source=SOURCE,candidate=DESTINATION,geometryScope='Localized outward garment folds at waist/chest/elbow/cuff; no skin/face/hair/boot edits',
    materialScope='Owned charcoal/amber finish clones for shared cloth/leather-detail/thread slots; pants and glove finish also uses these existing shared slots',
    materialChanges=material_changes,lods=rows,actionsExact=len(actions_before),restBonesExact=len(bones_before),texturesRewritten=False,
    proceduralFinishNeedsBakeBeforeRuntime=True,poseContactAcceptance=False,visualAccepted=False)))
