"""Bind V3 technical inspection to exact files, retaining V2 provenance."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[4]
REPORT=ROOT/'docs/p08/golden/ash/v3'
def receipt(name,marker):
    value=json.loads((REPORT/name).read_text(encoding='utf-8'))
    output='\n'.join(item.get('text','') for item in value['result']['content'])
    return json.JSONDecoder().raw_decode(output.split(marker,1)[1].lstrip())[0]
def file(path):
    absolute=ROOT/path
    return {'path':path,'sha256':hashlib.sha256(absolute.read_bytes()).hexdigest()}
audit=receipt('runtime-audit-mcp.json','ASH_RUNTIME_AUDIT ')
assert audit['bones']==45 and len(audit['clips'])==12
for mesh in audit['meshes']:
    assert mesh['degenerateTriangles']==mesh['degenerateUvTriangles']==mesh['nonmanifoldSharedEdges']==mesh['badWeights']==0
    assert mesh['finiteUV'] and mesh['maxInfluences']<=4
assert all(clip['nonFiniteVertices']==0 and clip['samples']==5 for clip in audit['clips'])
descriptor=json.loads((ROOT/'docs/p08/golden/ash/v2/descriptor-bind.json').read_text())
descriptor['purpose']='Isolated V3 technical inspection. Anatomical contact, clip and boot material refinement; visual fidelity and native performance are unaccepted.'
asset=descriptor['assets'][0];asset['id']='RB_Golden_Ash_V3'
asset['source']=file('ArtSource/P08/Golden/Ash/V3/RB_Golden_Ash_V3.blend')
asset['fbx']=file('Assets/RacingBois/Art/P08/Golden/Ash/V3/RB_Golden_Ash_V3.fbx')
for key in ['forwardMarker','leftMarker','rightMarker','rigRoot']:
    asset[key]=asset[key].replace('RB_Golden_Ash_V2','RB_Golden_Ash_V3')
for key in ['groundMarkers','requiredBones']:
    asset[key]=[value.replace('RB_Golden_Ash_V2','RB_Golden_Ash_V3') for value in asset[key]]
for lod in asset['lods']:lod['rendererPaths']=[path.replace('AshV2_','AshV3_') for path in lod['rendererPaths']]
for clip in asset['clips']:clip.update(asset['fbx'])
for material in asset['materials']:
    role=material['sourceName'].removeprefix('AshV2_').removesuffix('_Baked')
    if role not in ['BootLeather','Rubber']:continue
    material['sourceName']='AshV3_'+role+'_Baked'
    for key,channel in [('baseColor','BaseColor'),('normal','Normal'),('metallicSmoothness','MetallicSmoothness'),('occlusion','Occlusion')]:
        material[key]=file('Assets/RacingBois/Art/P08/Golden/Ash/V3/Textures/AshV3_'+role+'_'+channel+'.png')
contract=receipt('runtime-export-mcp.json','ASH_EXPORTED_RUNTIME ')
assert set(contract['materials'])=={material['sourceName'] for material in asset['materials']}
assert asset['restPose']=='bind'
(REPORT/'runtime-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
(REPORT/'export-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
(REPORT/'descriptor-bind.json').write_text(json.dumps(descriptor,indent=2)+'\n')
print(json.dumps({'descriptor':'docs/p08/golden/ash/v3/descriptor-bind.json','sourceSha256':asset['source']['sha256'],'fbxSha256':asset['fbx']['sha256'],'clips':len(asset['clips']),'bones':len(asset['requiredBones']),'materials':len(asset['materials']),'visualAccepted':False}))
