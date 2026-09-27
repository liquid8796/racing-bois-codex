"""Concept-derived rest-space leather panels/weathering, for real Blender baking."""
import bpy,math,json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
rig=bpy.data.objects['RB_P06_Rider_Rig'];PREFIX='RB_P06_Rider_L0_';ROOT='D:/Project/Unity/racing-bois/'
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
surface_obj=bpy.data.objects['AshV4_L0_Skin']
faces=[tuple(p.vertices) for p in surface_obj.data.polygons if surface_obj.data.materials[p.material_index].name in ['AshV2_TailoredClothing_Baked','AshV4_TailoredLeather_Source']]
cloth_tree=BVHTree.FromPolygons([v.co for v in surface_obj.data.vertices],faces,all_triangles=False)
sleeve_paths=[]
for side,sign in [('L',1),('R',-1)]:
    path=[]
    upper=rig.data.bones[PREFIX+'UpperArm_'+side];lower=rig.data.bones[PREFIX+'Forearm_'+side]
    upper_axis=(upper.tail_local-upper.head_local).normalized();lower_axis=(lower.tail_local-lower.head_local).normalized();joint_axis=(upper_axis+lower_axis).normalized()
    for part in ['UpperArm_','Forearm_']:
        bone=rig.data.bones[PREFIX+part+side];axis=(bone.tail_local-bone.head_local).normalized()
        for i in range(13):
            t=(.030+.930*i/12) if part=='UpperArm_' else (.025+.940*i/12)
            blend_t=max(0,min(1,(t-.65)/.35)) if part=='UpperArm_' else max(0,min(1,t/.35))
            blend_t=blend_t*blend_t*(3-2*blend_t)
            tangent=upper_axis.lerp(joint_axis,blend_t).normalized() if part=='UpperArm_' else joint_axis.lerp(lower_axis,blend_t).normalized()
            direction=Vector((sign*.82,-.57,0));direction=(direction-tangent*direction.dot(tangent)).normalized()
            center=bone.head_local+axis*bone.length*t
            point,normal,index,distance=cloth_tree.ray_cast(center+direction*.25,-direction,.5)
            assert point is not None,'Sleeve panel ray missed'
            path.append(point.copy())
    sleeve_paths.append(path)

def new_material(name):
    material=bpy.data.materials.get(name) or bpy.data.materials.new(name);material.use_nodes=True
    material.node_tree.nodes.clear();output=material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    shader=material.node_tree.nodes.new('ShaderNodeBsdfPrincipled');material.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface'])
    return material,material.node_tree.nodes,material.node_tree.links,material.node_tree.nodes['Principled BSDF']

def scalar(nodes,links,operation,a,b=None):
    node=nodes.new('ShaderNodeMath');node.operation=operation
    for i,value in enumerate([a,b]):
        if value is None:continue
        if isinstance(value,(int,float)):node.inputs[i].default_value=value
        else:links.new(value,node.inputs[i])
    return node.outputs[0]

def vector(nodes,links,operation,a,b=None):
    node=nodes.new('ShaderNodeVectorMath');node.operation=operation
    for i,value in enumerate([a,b]):
        if value is None:continue
        if isinstance(value,(tuple,list,Vector)):node.inputs[i].default_value=value
        else:links.new(value,node.inputs[i])
    return node.outputs['Value'] if operation in ['DOT_PRODUCT','LENGTH','DISTANCE'] else node.outputs['Vector']

def noise(nodes,links,position,scale,detail=3):
    node=nodes.new('ShaderNodeTexNoise');node.inputs['Scale'].default_value=scale;node.inputs['Detail'].default_value=detail
    links.new(position,node.inputs['Vector']);return node.outputs['Fac']

def mapped(nodes,links,value,low,high):
    node=nodes.new('ShaderNodeMapRange');node.inputs['To Min'].default_value=low;node.inputs['To Max'].default_value=high
    links.new(value,node.inputs['Value']);return node.outputs[0]

def blend(nodes,links,factor,a,b):
    node=nodes.new('ShaderNodeMixRGB')
    if isinstance(factor,(float,int)):node.inputs[0].default_value=factor
    else:links.new(factor,node.inputs[0])
    for index,value in [(1,a),(2,b)]:
        if isinstance(value,(tuple,list)):node.inputs[index].default_value=(*value[:3],1)
        else:links.new(value,node.inputs[index])
    return node.outputs[0]

def leather(name,panels=False):
    mat,nodes,links,bs=new_material(name)
    attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='AshV4_RestMeters';pos=attr.outputs['Vector']
    sep=nodes.new('ShaderNodeSeparateXYZ');links.new(pos,sep.inputs[0]);x,y,z=sep.outputs
    absx=scalar(nodes,links,'ABSOLUTE',x)
    mask=0
    if panels:
        # Reference yoke descends toward the arm, with continuous shoulder
        # transition. Old mask rose outward and stopped short of the sleeve.
        line=scalar(nodes,links,'SUBTRACT',1.483,scalar(nodes,links,'MULTIPLY',scalar(nodes,links,'SUBTRACT',absx,.06),.16))
        front=scalar(nodes,links,'LESS_THAN',scalar(nodes,links,'ABSOLUTE',scalar(nodes,links,'SUBTRACT',z,line)),.014)
        front=scalar(nodes,links,'MULTIPLY',front,scalar(nodes,links,'LESS_THAN',y,-.019))
        front=scalar(nodes,links,'MULTIPLY',front,scalar(nodes,links,'GREATER_THAN',absx,.058))
        front=scalar(nodes,links,'MULTIPLY',front,scalar(nodes,links,'LESS_THAN',absx,.235))
        backline=scalar(nodes,links,'SUBTRACT',1.467,scalar(nodes,links,'MULTIPLY',absx,.055))
        back=scalar(nodes,links,'LESS_THAN',scalar(nodes,links,'ABSOLUTE',scalar(nodes,links,'SUBTRACT',z,backline)),.018)
        back=scalar(nodes,links,'MULTIPLY',back,scalar(nodes,links,'GREATER_THAN',y,-.015))
        back=scalar(nodes,links,'MULTIPLY',back,scalar(nodes,links,'LESS_THAN',absx,.267))
        mask=scalar(nodes,links,'MAXIMUM',front,back)
        for path in sleeve_paths:
            for a,b in zip(path,path[1:]):
                axis=(b-a).normalized();length=(b-a).length
                delta=vector(nodes,links,'SUBTRACT',pos,a);t=vector(nodes,links,'DOT_PRODUCT',delta,axis)
                t=scalar(nodes,links,'MINIMUM',scalar(nodes,links,'MAXIMUM',t,0),length)
                scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[0].default_value=axis;links.new(t,scale.inputs['Scale'])
                radial=vector(nodes,links,'SUBTRACT',delta,scale.outputs[0])
                strip=scalar(nodes,links,'LESS_THAN',vector(nodes,links,'LENGTH',radial),.0145)
                mask=scalar(nodes,links,'MAXIMUM',mask,strip)
    base=blend(nodes,links,mask,(.037,.033,.028),(.37,.18,.050))
    worn=noise(nodes,links,pos,54,4);grain=noise(nodes,links,pos,370,3);fine=noise(nodes,links,pos,800,2)
    # Small leather pores and restrained scuff variation; no broad marble
    # pattern, artificial painted lighting or a flat concept projection.
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.38;ramp.color_ramp.elements[1].position=.65
    links.new(grain,ramp.inputs['Fac'])
    color=blend(nodes,links,scalar(nodes,links,'MULTIPLY',ramp.outputs['Color'],.16),base,(.083,.067,.049))
    links.new(color,bs.inputs['Base Color']);links.new(mapped(nodes,links,worn,.68,.85),bs.inputs['Roughness'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.34;bump.inputs['Distance'].default_value=.00060
    links.new(fine,bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    bs.inputs['Metallic'].default_value=0;bs.inputs['Coat Weight'].default_value=0
    mat['ash_v4_source_role']='TailoredLeather' if panels else 'LeatherDetails';mat['texture_size']=2048 if panels else 1024
    return mat

clothing=leather('AshV4_TailoredLeather_Source',True)
detail=leather('AshV4_LeatherDetails_Source',False)
helmet,nodes,links,bs=new_material('AshV4_HelmetEnamel_Source')
attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='AshV4_RestMeters';pos=attr.outputs['Vector']
vor=nodes.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=94;links.new(pos,vor.inputs['Vector'])
edge=scalar(nodes,links,'LESS_THAN',vor.outputs['Distance'],.046)
distribution=scalar(nodes,links,'GREATER_THAN',noise(nodes,links,pos,31,2),.58)
scratches=scalar(nodes,links,'MULTIPLY',edge,distribution)
chips=nodes.new('ShaderNodeTexVoronoi');chips.inputs['Scale'].default_value=83;links.new(pos,chips.inputs['Vector'])
chip_mask=scalar(nodes,links,'LESS_THAN',chips.outputs['Distance'],.085)
wear=scalar(nodes,links,'MAXIMUM',scratches,chip_mask)
base=blend(nodes,links,noise(nodes,links,pos,26,3),(.64,.59,.49),(.76,.70,.59))
links.new(blend(nodes,links,wear,base,(.16,.09,.040)),bs.inputs['Base Color'])
links.new(mapped(nodes,links,wear,.37,.69),bs.inputs['Roughness'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.00024
links.new(wear,bump.inputs['Height']);bump.invert=True;links.new(bump.outputs['Normal'],bs.inputs['Normal'])
bs.inputs['Metallic'].default_value=0;bs.inputs['Coat Weight'].default_value=0
helmet['ash_v4_source_role']='HelmetEnamel';helmet['texture_size']=1024
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin']
    for index,material in enumerate(obj.data.materials):
        if material.name=='AshV2_TailoredClothing_Baked':obj.data.materials[index]=clothing
        elif material.name=='AshV2_CharcoalLeather_Baked':obj.data.materials[index]=detail
        elif material.name=='AshV2_IvoryEnamel_Baked':obj.data.materials[index]=helmet
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_MATERIAL_SOURCES '+json.dumps({'materials':[clothing.name,detail.name,helmet.name],'sleevePaths':[[list(p) for p in path] for path in sleeve_paths],'proceduralSourcesRequireActualBakeBeforeRuntime':True,'visualAccepted':False}))
