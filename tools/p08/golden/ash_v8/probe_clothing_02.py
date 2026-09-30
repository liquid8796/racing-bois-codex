import bpy,json
from mathutils import Vector
if '/Ash/V8/' not in bpy.data.filepath.replace('\\','/'):raise RuntimeError('Owned V8 required')
obj=bpy.data.objects['AshV7_L0_Skin'];rig=bpy.data.objects['RB_P06_Rider_Rig']
groups={group.index:group.name for group in obj.vertex_groups}
rows=[]
ids={index for polygon in obj.data.polygons if polygon.material_index==6 for index in polygon.vertices}
bybone={}
for index in ids:
    vertex=obj.data.vertices[index];dominant=max(((group.weight,group.group) for group in vertex.groups),default=(0,-1))
    name=groups.get(dominant[1],'');bybone.setdefault(name,[]).append(vertex.co)
for name,points in bybone.items():
    rows.append(dict(bone=name,count=len(points),minimum=[min(p[i] for p in points) for i in range(3)],maximum=[max(p[i] for p in points) for i in range(3)]))
materials=[]
for name in ['AshV4_TailoredLeather_Baked','AshV4_LeatherDetails_Baked','AshV2_OchreThread_Baked']:
    mat=bpy.data.materials[name];bsdf=next(node for node in mat.node_tree.nodes if node.type=='BSDF_PRINCIPLED')
    materials.append(dict(name=name,baseColor=list(bsdf.inputs['Base Color'].default_value),roughness=bsdf.inputs['Roughness'].default_value,
       links=[dict(input=link.to_socket.name,node=link.from_node.name,output=link.from_socket.name) for link in mat.node_tree.links if link.to_node==bsdf],
       images=[dict(node=node.name,image=node.image.name,size=list(node.image.size),path=node.image.filepath) for node in mat.node_tree.nodes if node.type=='TEX_IMAGE' and node.image]))
print('ASH_V8_CLOTHING '+json.dumps(dict(regions=rows,bones=[dict(name=b.name,head=list(b.head_local),tail=list(b.tail_local)) for b in rig.data.bones if any(word in b.name for word in ['Torso','Arm','Hip'])],materials=materials)))
