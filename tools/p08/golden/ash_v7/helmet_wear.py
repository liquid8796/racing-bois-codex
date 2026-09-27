"""Project bounded cream/oxide wear onto the actual V7 shell, not old positions."""
import bpy,math,json,random
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';shell=bpy.data.objects['AshV7_L0_HelmetShell'];m=shell.data
tree=BVHTree.FromPolygons([v.co for v in m.vertices],[tuple(p.vertices) for p in m.polygons],all_triangles=False)
center=Vector((0,-.041,1.706));rng=random.Random(719204);strokes=[];chips=[]
for attempt in range(300):
 phi=rng.uniform(-math.pi,math.pi);theta=rng.uniform(.18,2.0);direction=Vector((math.sin(theta)*math.sin(phi),-math.sin(theta)*math.cos(phi),math.cos(theta)))
 p,n,index,d=tree.ray_cast(center+direction*.4,-direction,.8)
 if p is None or (p-center).dot(direction)<0:continue
 tangent=n.orthogonal().normalized();angle=rng.uniform(0,math.tau);tangent=tangent*math.cos(angle)+n.cross(tangent)*math.sin(angle)
 endpoint=p+tangent*rng.uniform(.0025,.0100);q,qn,idx,dist=tree.ray_cast(endpoint+n*.015,-n,.035)
 if q is not None:strokes.append((p,q,rng.uniform(.00032,.00065)))
 if len(strokes)==92:break
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
for i in range(48):
 phi=-math.pi+math.tau*(i+.35)/48;a=abs(phi);edge=1.27+.085*math.sin(min(1,a/.70)*math.pi*.5)**2*(1-smooth((a-.70)/.40))+.86*smooth((a-.58)/.65)-.22*smooth((a-1.75)/(math.pi-1.75));theta=edge-rng.uniform(.018,.055)
 direction=Vector((math.sin(theta)*math.sin(phi),-math.sin(theta)*math.cos(phi),math.cos(theta)));p,n,index,d=tree.ray_cast(center+direction*.4,-direction,.8)
 if p is not None:chips.append((p,rng.uniform(.00060,.0017)))
mat=bpy.data.materials.new('AshV7_Enamel_Source');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF'];attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='AshV7_RestMeters';position=attr.outputs['Vector']
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
def coverage(distance,width):
 node=nodes.new('ShaderNodeMapRange');node.clamp=True;node.interpolation_type='SMOOTHSTEP';node.inputs['From Min'].default_value=width*.45;node.inputs['From Max'].default_value=width;node.inputs['To Min'].default_value=1;node.inputs['To Max'].default_value=0;links.new(distance,node.inputs['Value']);return node.outputs[0]
mask=0
for p,q,width in strokes:
 axis=(q-p).normalized();delta=vector('SUBTRACT',position,p);t=scalar('MINIMUM',scalar('MAXIMUM',vector('DOT_PRODUCT',delta,axis),0),(q-p).length);scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[0].default_value=axis;links.new(t,scale.inputs['Scale']);distance=vector('LENGTH',vector('SUBTRACT',delta,scale.outputs[0]));mask=scalar('MAXIMUM',mask,coverage(distance,width))
for p,width in chips:mask=scalar('MAXIMUM',mask,coverage(vector('LENGTH',vector('SUBTRACT',position,p)),width))
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=24;noise.inputs['Detail'].default_value=2;links.new(position,noise.inputs['Vector'])
cream=nodes.new('ShaderNodeMixRGB');cream.inputs[1].default_value=(.64,.565,.445,1);cream.inputs[2].default_value=(.70,.635,.53,1);links.new(noise.outputs['Fac'],cream.inputs[0])
paint=nodes.new('ShaderNodeMixRGB');links.new(mask,paint.inputs[0]);links.new(cream.outputs[0],paint.inputs[1]);paint.inputs[2].default_value=(.14,.059,.018,1);links.new(paint.outputs[0],bs.inputs['Base Color'])
rough=nodes.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.33;rough.inputs['To Max'].default_value=.75;links.new(mask,rough.inputs['Value']);links.new(rough.outputs[0],bs.inputs['Roughness'])
bump=nodes.new('ShaderNodeBump');bump.invert=True;bump.inputs['Strength'].default_value=.23;bump.inputs['Distance'].default_value=.00027;links.new(mask,bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal']);bs.inputs['Metallic'].default_value=0;bs.inputs['Coat Weight'].default_value=0
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_HelmetShell'];obj.data.materials.clear();obj.data.materials.append(mat)
 attr=obj.data.attributes.get('AshV7_RestMeters') or obj.data.attributes.new('AshV7_RestMeters','FLOAT_VECTOR','POINT')
 for v in obj.data.vertices:attr.data[v.index].vector=v.co
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_PROJECTED_WEAR '+json.dumps({'scratches':len(strokes),'rimChips':len(chips),'strokeWidthMetres':[.00032,.00065],'chipRadiusMetres':[.0006,.0017],'projectedToCurrentV7Shell':True,'notOldV4StrokeCoordinates':True,'newSourceMaterial':mat.name,'visualAccepted':False}))
