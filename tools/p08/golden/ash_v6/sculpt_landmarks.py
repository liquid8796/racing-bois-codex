"""Recorded anatomical landmark correction; deterministic millimetre-scale fields."""
import bpy,math,json
from mathutils import Vector,Matrix
ROOT='D:/Project/Unity/racing-bois/'
assert '/Ash/V6/' in bpy.data.filepath.replace('\\','/')
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
# Each entry is a feature centre, XYZ support and peak XYZ displacement in
# metres. Supports localize the correction; no randomness or generic noise.
fields=[
 ('nasal-root',(0,-.1584,1.695),(.013,.022,.015),(0,-.0036,0)),
 ('nasal-dorsum',(0,-.172,1.678),(.011,.024,.019),(0,-.0035,.0005)),
 ('nasal-tip',(0,-.184,1.653),(.013,.016,.012),(0,-.0010,.0013)),
 ('chin-projection',(0,-.157,1.591),(.029,.024,.014),(0,-.0033,-.0035)),
 ('lower-lip',(0,-.165,1.620),(.026,.016,.006),(0,.0010,.0010)),
 ('philtrum',(0,-.164,1.634),(.010,.015,.007),(0,-.0012,0)),
]
for side in [-1,1]:
 fields.extend([
  ('malar-apex',(.052*side,-.135,1.674),(.016,.030,.014),(.0012*side,-.0010,.0003)),
  ('submalar-hollow',(.049*side,-.119,1.642),(.017,.035,.020),(-.0020*side,.0033,0)),
  ('mandibular-angle',(.062*side,-.070,1.611),(.020,.027,.019),(.0023*side,.0008,-.0030)),
  ('chin-corner',(.023*side,-.143,1.592),(.011,.025,.012),(.0010*side,-.0022,-.0018)),
  ('alar-side',(.017*side,-.159,1.650),(.009,.018,.010),(-.0013*side,0,.0004)),
  ('medial-brow',(.022*side,-.157,1.708),(.012,.021,.008),(0,-.0012,-.0008)),
  ('upper-eyelid',(.034*side,-.146,1.701),(.014,.014,.0035),(0,-.0006,-.0002)),
  ('mouth-corner',(.026*side,-.150,1.621),(.009,.018,.007),(0,.0004,.0007)),
 ])
reports=[]
for level in range(3):
 obj=bpy.data.objects['AshV6_L'+str(level)+'_Skin'];mesh=obj.data
 assert not obj.get('v6_landmark_sculpt',False)
 ids=set(i for p in mesh.polygons if mesh.materials[p.material_index].name in ['AshV4_Skin_Baked','AshV2_Brows_Baked'] for i in p.vertices)
 # Keep eyebrow fibers attached to their surface during the brow correction.
 ids.update(i for p in mesh.polygons if mesh.materials[p.material_index].name=='AshV4_Forelocks_Baked' and max(mesh.vertices[i].co.z for i in p.vertices)<1.717 for i in p.vertices)
 maximum=0;count=0
 for i in ids:
  p=mesh.vertices[i].co.copy()
  if p.z<1.56 or p.y>-.04:continue
  delta=Vector((0,0,0))
  for name,center,support,shift in fields:
   distance=sum(((p[k]-center[k])/support[k])**2 for k in range(3))
   if distance<12:delta+=Vector(shift)*math.exp(-distance)
  if delta.length<1e-8:continue
  before=[key.data[i].co.copy() for key in mesh.shape_keys.key_blocks]
  mesh.vertices[i].co=p+delta
  for key,co in zip(mesh.shape_keys.key_blocks,before):key.data[i].co=co+delta
  maximum=max(maximum,delta.length);count+=1
 mesh.update();obj['v6_landmark_sculpt']=True
 reports.append({'lod':level,'modifiedFaceVertices':count,'maximumDeltaMetres':maximum})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_FACE_LANDMARKS '+json.dumps({'fields':[{'feature':n,'center':p,'support':r,'peakDelta':d} for n,p,r,d in fields],'lods':reports,'rigOrActionEdits':False,'visualAccepted':False}))
