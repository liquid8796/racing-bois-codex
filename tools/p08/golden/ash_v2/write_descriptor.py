"""Write an exact-input diagnostic descriptor only after the current DCC audit."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[4]
REPORT=ROOT/'docs/p08/golden/ash/v2'
audit=json.loads((REPORT/'runtime-audit.json').read_text())
contract=json.loads((REPORT/'export-contract.json').read_text())
maps=json.loads((REPORT/'pbr-maps.json').read_text())
assert audit['bones']==45 and len(audit['clips'])==12
for mesh in audit['meshes']:
    assert mesh['degenerateTriangles']==mesh['degenerateUvTriangles']==mesh['nonmanifoldSharedEdges']==mesh['badWeights']==0,mesh
    assert mesh['finiteUV'] and mesh['maxInfluences']<=4
for clip in audit['clips']:assert clip['samples']==5 and clip['nonFiniteVertices']==0
def file(path):
    path=Path(path);absolute=path if path.is_absolute() else ROOT/path
    return {'path':absolute.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(absolute.read_bytes()).hexdigest()}
fbx=file('Assets/RacingBois/Art/P08/Golden/Ash/V2/RB_Golden_Ash_V2.fbx')
materials=[]
for material in maps['materials']:
    values={key:file(material['files'][channel]['path']) for key,channel in [('baseColor','BaseColor'),('normal','Normal'),('metallicSmoothness','MetallicSmoothness'),('occlusion','Occlusion')]}
    values.update(sourceName=material['runtimeMaterial'],maxSize=material['size'],normalScale=1,
                  transparent=material['transparent'],doubleSided=material['doubleSided'],opacity=1)
    materials.append(values)
assert {m['sourceName'] for m in materials}==set(contract['materials'])
# Exact real Unity subasset names were verified through the root's live Unity
# importer probe; __preview__ editor-only subassets are deliberately excluded.
names=['Ride','LeanLeft','LeanRight','AttackLeft','AttackRight','KickLeft','KickRight','Hit','Fall','Run','Remount','Idle']
clips=[dict(fbx,name='RB_P06_Rider_Rig|RB_'+name) for name in names]
asset={
 'id':'RB_Golden_Ash_V2','kind':'rider',
 'concept':file('ArtSource/Concepts/P08/Golden/ash-v2.png'),
 'conceptReview':file('ArtSource/Concepts/P08/Golden/ash-v2-review.md'),
 'source':file('ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend'),'fbx':fbx,
 'modelRotationEuler':{'x':0,'y':180,'z':0},
 'minimumSize':{'x':.50,'y':1.68,'z':.22},'maximumSize':{'x':1.30,'y':1.95,'z':.75},
 'maximumBelowGround':.025,'materials':materials,
 'lods':[{'height':height,'rendererPaths':['RB_P06_Rider_Rig/AshV2_L'+str(i)+'_Skin']} for i,height in enumerate([.34,.14,.025])],
 'forwardMarker':contract['forwardMarker'],'groundMarkers':contract['groundMarkers'],
 'leftMarker':contract['leftMarker'],'rightMarker':contract['rightMarker'],
 'rigRoot':'RB_P06_Rider_Rig','requiredBones':contract['bonePaths'],'clips':clips,
 'colliders':[{'type':'capsule','center':{'x':0,'y':.925,'z':0},'radius':.275,'height':1.85,'direction':1}],
 'isStatic':False,
}
descriptor={'schema':1,'purpose':'Isolated technical inspection only. Concept fidelity and native performance are not accepted.','assets':[asset]}
(REPORT/'descriptor.json').write_text(json.dumps(descriptor,indent=2)+'\n')
print(json.dumps({'descriptor':'docs/p08/golden/ash/v2/descriptor.json','sourceSha256':asset['source']['sha256'],'fbxSha256':fbx['sha256'],
                  'clips':len(clips),'materials':len(materials),'bones':len(asset['requiredBones']),'visualAccepted':False}))
