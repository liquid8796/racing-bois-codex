import bpy,math,json,random
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';obj=bpy.data.objects['AshV4_L0_Skin'];mat=bpy.data.materials['AshV4_HelmetEnamel_Source']
faces=[tuple(p.vertices) for p in obj.data.polygons if obj.data.materials[p.material_index]==mat]
tree=BVHTree.FromPolygons([v.co for v in obj.data.vertices],faces,all_triangles=False)
center=Vector((0,-.045,1.704));rng=random.Random(710482);strokes=[]
for attempt in range(160):
    phi=rng.uniform(0,math.tau);theta=rng.uniform(.20,2.05);direction=Vector((math.sin(theta)*math.sin(phi),-math.sin(theta)*math.cos(phi),math.cos(theta)))
    p,n,index,d=tree.ray_cast(center+direction*.4,-direction,.8)
    if p is None or (p-center).dot(direction)<0:continue
    tangent=n.orthogonal().normalized();angle=rng.uniform(0,math.tau);tangent=tangent*math.cos(angle)+n.cross(tangent)*math.sin(angle)
    length=rng.uniform(.002,.010);end=p+tangent*length
    q,qn,index,d=tree.ray_cast(end+n*.015,-n,.035)
    if q is not None:strokes.append((p,q,rng.uniform(.00020,.00040)))
    if len(strokes)>=48:break
nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled');links.new(bs.outputs['BSDF'],output.inputs['Surface'])
attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='AshV4_RestMeters';position=attr.outputs['Vector']
def scalar(operation,a,b=None):
    node=nodes.new('ShaderNodeMath');node.operation=operation
    for i,v in enumerate([a,b]):
        if v is None:continue
        if isinstance(v,(int,float)):node.inputs[i].default_value=v
        else:links.new(v,node.inputs[i])
    return node.outputs[0]
def vector(operation,a,b=None):
    node=nodes.new('ShaderNodeVectorMath');node.operation=operation
    for i,v in enumerate([a,b]):
        if v is None:continue
        if isinstance(v,Vector):node.inputs[i].default_value=v
        else:links.new(v,node.inputs[i])
    return node.outputs['Value'] if operation in ['LENGTH','DOT_PRODUCT'] else node.outputs['Vector']
mask=0
for p,q,width in strokes:
    axis=(q-p).normalized();length=(q-p).length;delta=vector('SUBTRACT',position,p)
    t=scalar('MINIMUM',scalar('MAXIMUM',vector('DOT_PRODUCT',delta,axis),0),length)
    scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[0].default_value=axis;links.new(t,scale.inputs['Scale'])
    distance=vector('LENGTH',vector('SUBTRACT',delta,scale.outputs[0]))
    line=scalar('LESS_THAN',distance,width);mask=scalar('MAXIMUM',mask,line)
for p,q,width in strokes[::4]:
    point=scalar('LESS_THAN',vector('LENGTH',vector('SUBTRACT',position,p)),width*2.1)
    mask=scalar('MAXIMUM',mask,point)
color=nodes.new('ShaderNodeMixRGB');color.inputs[1].default_value=(.68,.625,.526,1);color.inputs[2].default_value=(.18,.106,.05,1)
links.new(mask,color.inputs[0]);links.new(color.outputs[0],bs.inputs['Base Color'])
rough=nodes.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.39;rough.inputs['To Max'].default_value=.67;links.new(mask,rough.inputs['Value']);links.new(rough.outputs[0],bs.inputs['Roughness'])
bump=nodes.new('ShaderNodeBump');bump.invert=True;bump.inputs['Strength'].default_value=.21;bump.inputs['Distance'].default_value=.00018;links.new(mask,bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
bs.inputs['Metallic'].default_value=0;bs.inputs['Coat Weight'].default_value=0
mat['ash_v4_source_role']='HelmetEnamel';mat['texture_size']=1024
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_HELMET_WEAR '+json.dumps({'scratches':len(strokes),'geometrySurfaceProjected':True,'previousVoronoiCrackleRemoved':True,'scratchEndpoints':[[list(p),list(q),width] for p,q,width in strokes],'visualAccepted':False}))
