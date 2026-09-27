import bpy,json
material=bpy.data.materials['AshV6_Skin_Source'];rows=[]
for node in material.node_tree.nodes:
 if node.type=='MATH' and node.operation=='MULTIPLY_ADD':
  rows.append({'formerAddend':node.inputs[2].default_value});node.operation='MULTIPLY'
print('ASH_V6_PIGMENT_FACTOR '+json.dumps({'correctedNodes':rows,'factorUpperBound':.17}))
