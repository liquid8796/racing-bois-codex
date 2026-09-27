"""Repair only collar/upper-garment deformation; protect contacts and animation."""
import bpy,json
from mathutils import Matrix,Vector
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
PREFIX='RB_P06_Rider_L0_';reports=[]
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];mesh=obj.data;adj=[set() for _ in mesh.vertices]
 for edge in mesh.edges:a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
 todo=set(range(len(mesh.vertices)));collar=set();tab=set();snap=set();stitch=set();obsolete=set()
 roles={i:set() for i in range(len(mesh.vertices))}
 for p in mesh.polygons:
  for i in p.vertices:roles[i].add(mesh.materials[p.material_index].name)
 while todo:
  first=todo.pop();found={first};queue=[first]
  while queue:
   for i in adj[queue.pop()]:
    if i in todo:todo.remove(i);found.add(i);queue.append(i)
  points=[mesh.vertices[i].co for i in found];low=[min(p[k] for p in points) for k in range(3)];high=[max(p[k] for p in points) for k in range(3)];names=set(n for i in found for n in roles[i])
  if low[2]<1.53 or high[2]>1.585:continue
  if names=={'AshV2_AgedBrass_Baked'} and low[0]<-.045 and high[0]<-.03 and low[1]>-.085:obsolete.update(found);continue
  if max(abs(low[0]),abs(high[0]))>.135:continue
  if not names.issubset({'AshV4_LeatherDetails_Baked','AshV2_OchreThread_Baked','AshV2_AgedBrass_Baked'}):continue
  collar.update(found)
  if low[0]>-.050 and high[0]<.031 and high[1]<-.085:
   if names=={'AshV4_LeatherDetails_Baked'}:tab.update(found)
   elif names=={'AshV2_AgedBrass_Baked'}:snap.update(found)
   else:stitch.update(found)
 changes=0;maximum=0
 for v in mesh.vertices:
  names=roles[v.index]
  garment=names.issubset({'AshV4_LeatherDetails_Baked','AshV4_TailoredLeather_Baked','AshV2_OchreThread_Baked','AshV2_AgedBrass_Baked'})
  central=1.445<v.co.z<1.585 and abs(v.co.x)<.145 and -.17<v.co.y<.11
  if not garment or not central or v.index in obsolete:continue
  weights={obj.vertex_groups[g.group].name:g.weight for g in v.groups}
  if v.index in collar:weights={PREFIX+'Torso':1.0}
  elif PREFIX+'Head' in weights:
   moved=weights.pop(PREFIX+'Head');weights[PREFIX+'Torso']=weights.get(PREFIX+'Torso',0)+moved
  else:continue
  for g in list(v.groups):obj.vertex_groups[g.group].remove([v.index])
  total=sum(weights.values())
  for name,w in weights.items():obj.vertex_groups[name].add([v.index],w/total,'REPLACE')
  changes+=1
 # The V4 tab sat behind the front collar, where skin showed through the
 # overlap. Bring the tab, its stitch and snap to the actual outer surface.
 for i in tab|snap|stitch:
  p=mesh.vertices[i].co.copy();delta=Vector((0,-.014,0))
  if i in tab|stitch and p.x>0:delta.x=.015*(p.x/.027)
  before=[k.data[i].co.copy() for k in mesh.shape_keys.key_blocks];mesh.vertices[i].co=p+delta
  for key,co in zip(mesh.shape_keys.key_blocks,before):key.data[i].co=co+delta
  maximum=max(maximum,delta.length)
 # Store exact obsolete indices for a topology-preserving face extraction.
 obj['v7_obsolete_snap_vertices']=list(sorted(obsolete));obj['v7_collar_vertices']=list(sorted(collar));obj['v7_tab_vertices']=list(sorted(tab));obj['v7_snap_vertices']=list(sorted(snap))
 mesh.update();reports.append({'lod':level,'changedUpperGarmentWeights':changes,'rigidCollarVertices':len(collar),'tabVertices':len(tab),'snapVertices':len(snap),'obsoleteSideSnapVertices':len(obsolete),'maximumTabTranslationMetres':maximum})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_COLLAR_BINDING '+json.dumps({'lods':reports,'scope':'central collar/upper garment only; Head influence transferred to Torso','animationOrRestBoneChanges':False,'visualAccepted':False}))
