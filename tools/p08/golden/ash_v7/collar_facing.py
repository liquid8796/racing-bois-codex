import bpy,json,math
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
rows=[]
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];m=obj.data;ids=list(obj['v7_tab_vertices']);xmin=min(m.vertices[i].co.x for i in ids);xmax=max(m.vertices[i].co.x for i in ids);zmin=min(m.vertices[i].co.z for i in ids);zmax=max(m.vertices[i].co.z for i in ids);radius=.0030;changed=0
 for i in ids:
  p=m.vertices[i].co.copy();cx=max(xmin+radius,min(xmax-radius,p.x));cz=max(zmin+radius,min(zmax-radius,p.z));dx=p.x-cx;dz=p.z-cz;length=math.sqrt(dx*dx+dz*dz)
  if length<=radius:continue
  target=p.copy();target.x=cx+dx*radius/length;target.z=cz+dz*radius/length;delta=target-p;before=[k.data[i].co.copy() for k in m.shape_keys.key_blocks];m.vertices[i].co=target
  for key,co in zip(m.shape_keys.key_blocks,before):key.data[i].co=co+delta
  changed+=1
 # A real inner facing closes the old skin-coloured slit under the fastener.
 verts=[];faces=[];cols=9;row_count=4
 for side in range(2):
  for row in range(row_count):
   for col in range(cols):
    x=-.032+.067*col/(cols-1);z=1.525+.031*row/(row_count-1);y=-.105+.010*(x/.038)**2+side*.0016;verts.append((x,y,z))
    if row and col:
     i=side*cols*row_count+row*cols+col;faces.append((i-cols-1,i-cols,i,i-1) if side==0 else (i-1,i,i-cols,i-cols-1))
 total=cols*row_count;border=list(range(cols))+[r*cols+cols-1 for r in range(1,row_count)]+list(range(total-2,total-cols-1,-1))+[r*cols for r in range(row_count-2,0,-1)]
 for i,a in enumerate(border):b=border[(i+1)%len(border)];faces.append((a,b,b+total,a+total))
 data=bpy.data.meshes.new('AshV7_CollarFacing');data.from_pydata(verts,[],faces);data.update();part=bpy.data.objects.new('AshV7_L'+str(level)+'_CollarFacing',data);bpy.context.scene.collection.objects.link(part);part.parent=rig;data.materials.append(bpy.data.materials['AshV3_Rubber_Baked']);layer=data.uv_layers.new(name='UV0')
 sample=next(p for p in m.polygons if m.materials[p.material_index].name=='AshV3_Rubber_Baked');centre=sum((m.uv_layers[0].data[i].uv for i in sample.loop_indices),m.uv_layers[0].data[sample.loop_indices[0]].uv*0)/len(sample.loop_indices)
 for p in data.polygons:
  p.use_smooth=True
  for j,i in enumerate(p.loop_indices):layer.data[i].uv=(centre.x+.0004*math.cos(j*math.tau/len(p.vertices)),centre.y+.0004*math.sin(j*math.tau/len(p.vertices)))
 group=part.vertex_groups.new(name='RB_P06_Rider_L0_Torso');group.add(list(range(len(verts))),1,'REPLACE');mod=part.modifiers.new('Stable torso facing','ARMATURE');mod.object=rig;part.hide_render=level!=0;part.hide_set(level!=0);part['intentional_small_finish_tile']=True
 rows.append({'lod':level,'tabCornersRoundedVertices':changed,'facingVertices':len(verts),'newMaterialCount':0,'finish':'shared matte black, existing verified rubber PBR maps'})
rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_COLLAR_FACING '+json.dumps(rows))
