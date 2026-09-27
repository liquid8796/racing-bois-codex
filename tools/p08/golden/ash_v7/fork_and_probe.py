import bpy,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',load_ui=False,use_scripts=False)
bpy.data.objects['RB_Golden_Ash_V6'].name='RB_Golden_Ash_V7'
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for level in range(3):bpy.data.objects['AshV6_L'+str(level)+'_Skin'].name='AshV7_L'+str(level)+'_Skin'
obj=bpy.data.objects['AshV7_L0_Skin'];m=obj.data;adj=[set() for _ in m.vertices]
for e in m.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
remaining=set(v.index for v in m.vertices);components=[]
while remaining:
 first=remaining.pop();found={first};queue=[first]
 while queue:
  for i in adj[queue.pop()]:
   if i in remaining:remaining.remove(i);found.add(i);queue.append(i)
 if min(m.vertices[i].co.z for i in found)>1.45 and max(m.vertices[i].co.z for i in found)<1.60:
  points=[m.vertices[i].co for i in found];roles=sorted(set(m.materials[p.material_index].name for p in m.polygons if p.vertices[0] in found));groups={}
  for i in found:
   for g in m.vertices[i].groups:
    name=obj.vertex_groups[g.group].name;groups[name]=max(groups.get(name,0),g.weight)
  components.append({'count':len(found),'firstIndex':min(found),'min':[min(p[k] for p in points) for k in range(3)],'max':[max(p[k] for p in points) for k in range(3)],'roles':roles,'maximumWeights':groups})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_COLLAR_PROBE '+json.dumps({'components':components,'bones':[(b.name,list(b.head_local),list(b.tail_local)) for b in rig.data.bones if b.name.endswith(('Hip','Torso','Neck','Head'))]}))
