"""Subtle beard-region pigment and restrained face roughness, baked from 3D."""
import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
mat=bpy.data.materials['AshV4_Skin_Baked'].copy();mat.name='AshV6_Skin_Source';mat.use_fake_user=True
nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF'];base=bs.inputs['Base Color'].links[0].from_socket
attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='AshV6_RestMeters'
def mathop(operation,a,b=None):
 n=nodes.new('ShaderNodeMath');n.operation=operation
 for i,v in enumerate([a,b]):
  if v is None:continue
  if isinstance(v,(int,float)):n.inputs[i].default_value=v
  else:links.new(v,n.inputs[i])
 return n.outputs[0]
def ellipse(center,radii):
 n=nodes.new('ShaderNodeVectorMath');n.operation='SUBTRACT';links.new(attr.outputs['Vector'],n.inputs[0]);n.inputs[1].default_value=center
 s=nodes.new('ShaderNodeVectorMath');s.operation='DIVIDE';links.new(n.outputs[0],s.inputs[0]);s.inputs[1].default_value=radii
 d=nodes.new('ShaderNodeVectorMath');d.operation='LENGTH';links.new(s.outputs[0],d.inputs[0])
 ramp=nodes.new('ShaderNodeMapRange');ramp.clamp=True;ramp.interpolation_type='SMOOTHERSTEP';ramp.inputs['From Min'].default_value=.25;ramp.inputs['From Max'].default_value=1.0;ramp.inputs['To Min'].default_value=1;ramp.inputs['To Max'].default_value=0;links.new(d.outputs['Value'],ramp.inputs['Value']);return ramp.outputs[0]
mask=ellipse((0,-.126,1.592),(.063,.054,.042))
for center,radii in [((-.053,-.095,1.624),(.029,.045,.046)),((.053,-.095,1.624),(.029,.045,.046)),((0,-.161,1.637),(.029,.016,.005))]:mask=mathop('MAXIMUM',mask,ellipse(center,radii))
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=980;noise.inputs['Detail'].default_value=2;links.new(attr.outputs['Vector'],noise.inputs['Vector'])
mix=nodes.new('ShaderNodeMixRGB');links.new(mathop('MULTIPLY',mask,mathop('MULTIPLY',noise.outputs['Fac'],.17)),mix.inputs[0])
links.new(base,mix.inputs[1]);mix.inputs[2].default_value=(.036,.026,.019,1);links.new(mix.outputs[0],bs.inputs['Base Color'])
for link in list(bs.inputs['Roughness'].links):links.remove(link)
bs.inputs['Roughness'].default_value=.61
mat['ash_v6_source_role']='Skin';mat['texture_size']=2048
for level in range(3):
 obj=bpy.data.objects['AshV6_L'+str(level)+'_Skin'];a=obj.data.attributes.new('AshV6_RestMeters','FLOAT_VECTOR','POINT')
 for v in obj.data.vertices:a.data[v.index].vector=v.co
 for i,m in enumerate(obj.data.materials):
  if m.name=='AshV4_Skin_Baked':obj.data.materials[i]=mat
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_SKIN_SOURCE '+json.dumps({'pigmentRegion':'chin, mandibular edges, narrow upper lip','maximumMask':.17,'roughness':.61,'requiresBake':True,'visualAccepted':False}))
