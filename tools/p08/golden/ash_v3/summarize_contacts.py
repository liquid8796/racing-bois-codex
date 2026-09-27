from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[4];REPORT=ROOT/'docs/p08/golden/ash/v3'
receipt=json.loads((REPORT/'contact-rays-final-mcp.json').read_text())
text='\n'.join(item.get('text','') for item in receipt['result']['content'])
data=json.JSONDecoder().raw_decode(text.split('ASH_V3_ACTUAL_CONTACT_RAYS ',1)[1].lstrip())[0]
summary={'scope':data['scope'],'productionAccepted':False,'grips':{},'soleClearanceMeters':{},'seat':data['seat']}
for side,grip in data['grips'].items():
    rows=[row for row in grip['rays'] if row['along']==0]
    hits=[row['hit']['distance'] for row in rows if row['hit']]
    summary['grips'][side]={'gripRadiusMeters':grip['radius'],'centreRayHits':len(hits),'centreRaySamples':len(rows),'minimumCentreRayClearanceMeters':min(hits)-grip['radius'],'maximumCentreRayClearanceMeters':max(hits)-grip['radius'],'missingAngularSamplesDegrees':[row['angle'] for row in rows if row['hit'] is None],'notAnExactCollisionOrFidelityProof':True}
for side,foot in data['feet'].items():summary['soleClearanceMeters'][side]=foot['soleAbovePegCentre']['distance']-.1-foot['pegRadius']
(REPORT/'actual-contact-rays.json').write_text(json.dumps(data,indent=2)+'\n')
(REPORT/'contact-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
