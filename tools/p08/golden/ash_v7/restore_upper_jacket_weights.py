"""Restore the original jacket binding outside separately repaired collar pieces."""
import bpy,json
ROOT='D:/Project/Unity/racing-bois/';roles={'AshV4_LeatherDetails_Baked','AshV4_TailoredLeather_Baked','AshV2_OchreThread_Baked','AshV2_AgedBrass_Baked','AshV3_Rubber_Baked'}
def capture(version):
 output=[]
 for level in range(3):
  obj=bpy.data.objects['AshV'+str(version)+'_L'+str(level)+'_Skin'];m=obj.data;ids=set(i for p in m.polygons if m.materials[p.material_index].name in roles for i in p.vertices if 1.425<m.vertices[i].co.z<1.605 and abs(m.vertices[i].co.x)<.32);by_position={}
  for i in ids:by_position[tuple(m.vertices[i].co)]=[(obj.vertex_groups[g.group].name,g.weight) for g in m.vertices[i].groups]
  output.append(by_position)
 return output
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',load_ui=False,use_scripts=False);original=capture(6)
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',load_ui=False,use_scripts=False);rows=[]
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];collar=set(obj['v7_collar_vertices'])|set(obj['v7_facing_vertices']);count=0
 for v in obj.data.vertices:
  if v.index in collar:continue
  values=original[level].get(tuple(v.co))
  if values is None:continue
  before=sorted((obj.vertex_groups[g.group].name,g.weight) for g in v.groups)
  if before==sorted(values):continue
  for g in list(v.groups):obj.vertex_groups[g.group].remove([v.index])
  for name,w in values:obj.vertex_groups[name].add([v.index],w,'REPLACE')
  count+=1
 obj.data.update();rows.append({'lod':level,'restoredOriginalJacketWeightVertices':count,'collarPreservedVertices':len(collar)})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_JACKET_WEIGHT_RESTORE '+json.dumps({'lods':rows,'discardedOverbroadGeometryFit':True,'skinOrGloveBootEdits':False,'visualAccepted':False}))
