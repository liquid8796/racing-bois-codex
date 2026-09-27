"""Bind the bounded Spark V2 source, real MCP receipts and rendered review images; no export or acceptance."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
FOLDER=ROOT/'docs/p08/golden/spark/v2'
sys.path.insert(0,str(ROOT/'tools/blender'))
from result_status import execution_failure

def row(path):
    data=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}

def receipt(name,prefix):
    path=FOLDER/(name+'-mcp.json');payload=json.loads(path.read_text())
    failure=execution_failure(payload['result'],payload['tool'])
    if failure:raise ValueError(failure)
    text='\n'.join(block.get('text','') for block in payload['result']['content'])
    at=text.index(prefix)+len(prefix)
    return json.JSONDecoder().raw_decode(text[at:])[0]

def main():
    original=json.loads((FOLDER/'before-manifest.json').read_text())['inputs']
    changes=[entry['path'] for entry in original if row(ROOT/entry['path'])['sha256']!=entry['sha256']]
    if changes:raise ValueError('Immutable original inputs changed: '+', '.join(changes))
    geometry=receipt('geometry-audit-05','SPARK_V2_AUDIT=')
    if geometry['geometryIssues'] or geometry['chainIntersections'] or geometry['tankContactsWithNamedStructure']:
        raise ValueError('Scoped mechanical checks are not clear')
    seat=receipt('seat-contact-05','SPARK_V2_SEAT_CONTACT=')
    if abs(seat['afterSurfaceZ']-.800)>1e-5 or not seat['contactMarkerUnchanged']:raise ValueError('Seat contact moved')
    source=ROOT/'ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_refined05.blend'
    if source.open('rb').read(4)!=bytes.fromhex('28b52ffd'):raise ValueError('Expected native compressed Blender source')
    captures=[]
    for view in ['quarter','side']:
        capture=receipt('render-05-'+view,'SPARK_V2_RENDER=')
        if capture['view']!=view or capture['visualAccepted'] or capture['exported']:raise ValueError('Incorrect capture scope')
        image=ROOT/'docs/p08/golden/spark/v2'/('05-'+view+'.png')
        captures.append({'view':view,**row(image)})
    mechanical=receipt('mechanical-clearance-03c','SPARK_V2_MECHANICAL_CLEARANCE=')
    records=['addon-status','refine-01','mechanical-clearance-03c','tank-topology-04','seat-contact-05','geometry-audit-05','joints-04','render-05-quarter','render-05-side']
    result={'schema':1,'source':row(source),'nativeCompressed':True,'captures':captures,
        'concepts':[entry for entry in original if entry['path'].endswith(('spark-v1.png','spark-v1-side.png'))],
        'originalInputCount':len(original),'originalInputChanges':changes,'mechanicalRefinement':{'drivePlaneMetres':mechanical['drivePlaneMetres'],
            'downstreamExhaustOutboardShiftMetres':mechanical['silencerOutboardShiftMetres'],'changedInheritedMeshes':len(mechanical['changedMeshes'])},
        'scopedGeometryChecks':geometry,'seatSurfaceZ':seat['afterSurfaceZ'],'receipts':[row(FOLDER/(name+'-mcp.json')) for name in records],
        'review':row(FOLDER/'DESIGN_REVIEW.md'),'visualAccepted':False,'exported':False,'unityUpdated':False,
        'scope':'Bounded engine/tank/seat/mechanical refinement. Static named checks only; concept mismatch remains. No LOD/export/native-player/performance acceptance.'}
    (FOLDER/'review-snapshot.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'source':result['source'],'captures':captures,'originalInputChanges':changes,'visualAccepted':False,'exported':False},indent=2))

if __name__=='__main__':main()
