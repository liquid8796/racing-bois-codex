"""Read-only bounded WAN evidence; never edits source or changes the running probe."""
from pathlib import Path
import datetime,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
RUN='20260926T214515Z';report=ROOT/'docs/p10/network'/RUN/'probe.json'
data=json.loads(report.read_text());trace=data['correctionTrace'];rows=[]
for episode in trace['episodes']:
    before=episode['Before'];after=episode['After']
    if before['RawPose']['Mode']!='Riding' or after['RawPose']['Mode']!='Falling':continue
    recovered=[event for event in after['Events'] if event['Kind']=='PedestrianRecovered' and before['Authority']['Tick']<event['Tick']<=after['Authority']['Tick']]
    for event in recovered:
        pedestrian=next((p for p in before['Pedestrians'] if p['Id']==event['SourceId']),None)
        if pedestrian is None or pedestrian['Mode']!=2:continue
        expected=before['Authority']['Tick']+180-pedestrian['ModeAgeTicks']
        crashes=[event for event in after['Events'] if event['Kind']=='Crash' and event['SourceId']==before['RiderId'] and before['Authority']['Tick']<event['Tick']<=after['Authority']['Tick']]
        rows.append({'peer':episode['Peer'],'atSeconds':episode['At'],'deltaMeters':episode['Delta'],'presentedDeltaMeters':episode['PresentedDelta'],
            'noNeighborCounterfactualDeltaMeters':episode['NoNeighborDelta'],'replayVerifiedBefore':episode['OldReplayVerified'],'replayVerifiedAfter':episode['NewReplayVerified'],
            'beforeAuthorityTick':before['Authority']['Tick'],'afterAuthorityTick':after['Authority']['Tick'],'comparedPredictionTick':after['Predicted']['Tick'],
            'rttMilliseconds':before['RttMs'],'leadTicks':before['LeadTicks'],'pedestrianId':pedestrian['Id'],'stumbledAgeBefore':pedestrian['ModeAgeTicks'],
            'expectedRecoveryTickFromKnownAge':expected,'observedRecoveryTick':event['Tick'],'recoveryTickMatches':expected==event['Tick'],'observedCrashes':crashes})
sources=['Packages/com.racingbois.foundation/Runtime/Simulation/RiderPrediction.cs','Packages/com.racingbois.foundation/Runtime/Simulation/PedestrianSimulation.cs','Packages/com.racingbois.foundation/Runtime/Simulation/DrivingDynamics.cs']
result={'generatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runId':RUN,'runStatusAtRead':data['status'],'elapsedSecondsAtRead':data['elapsedSeconds'],
 'acceptedEqualTargetSnapshots':trace['acceptedEqualTargetSnapshots'],'maximumCorrectionMeters':trace['maximumCorrection'],'replayMismatches':trace['replayMismatches'],
 'modeGroups':trace['modes'],'pedestrianRecoveryCorrespondences':rows,
 'sourceFiles':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
 'finding':'Authoritative PedestrianSimulation increments age and recovers Stumbled pedestrians at 180 ticks; RiderPrediction.AdvanceNeighbors leaves non-Walking pedestrian mode/age unchanged. ResolveContacts skips Stumbled pedestrians. Corresponding recovery/crash events explain an additional deterministic prediction gap distinct from remote rider immunity.',
 'limits':'Read-only live bounded trace plus exact source discrepancy. No production/probe/source edits, no new predictor implementation, no rendered Unity smoothness acceptance. Timing correspondence is preserved separately from any future isolated regression/counterfactual implementation.'}
out=ROOT/'docs/p09/releases/e/correction-observations.json';out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'runStatus':data['status'],'maximumCorrectionMeters':trace['maximumCorrection'],'recoveryCorrespondences':len(rows),'report':out.relative_to(ROOT).as_posix()}))
