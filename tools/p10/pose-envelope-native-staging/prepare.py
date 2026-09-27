"""Prepare namespace-isolated source and four trace-bound native comparisons.

Does not install into Assets, call Unity, mutate the frozen candidate, or run a player.
"""
from pathlib import Path
import hashlib
import json
import math
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
BASE=ROOT/'tools/p10/pose-envelope-staging'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
manifest=json.loads((BASE/'candidate-manifest.json').read_text())
expected={Path(row['candidate']).name:row for row in manifest['files']}
copies=[]
for name in ['VisualPoseEnvelope.cs','UnityVisualPoseEnvelope.cs','PresentationContinuityScope.cs']:
    source=BASE/name;data=source.read_bytes();assert sha(source)==expected[name]['candidateSha256']
    old=b'namespace RacingBois.Client.Presentation';new=b'namespace RacingBois.Diagnostics.PoseEnvelopePreview'
    assert data.count(old)==1
    changed=data.replace(old,new);destination=HERE/'Runtime'/name;write(destination,changed)
    copies.append({'source':source.relative_to(ROOT).as_posix(),'sourceSha256':sha(source),'path':destination.relative_to(ROOT).as_posix(),
        'sha256':sha(destination),'transform':'one literal namespace substitution only','from':old.decode(),'to':new.decode()})
# A separate, explicit comparison fork. The three baseline copies above remain
# namespace-only. Halving translation speed needs a longer finite error window.
original=(HERE/'Runtime/VisualPoseEnvelope.cs').read_text()
changes={
    'public sealed class VisualPoseEnvelope':'public sealed class VisualPoseEnvelope20Comparison',
    'MaximumCorrectionSpeed = 40f':'MaximumCorrectionSpeed = 20f',
    'MaximumDurationSeconds = .375':'MaximumDurationSeconds = .75',
    'MaximumBurstSeconds = .6':'MaximumBurstSeconds = 1.2',
    '    public enum VisualPoseResetReason { None, Initialization, ExplicitReset, ClockGap, ClockRewind, Teleport, OffsetBudget, BurstBudget, FrozenResume }\n':''}
variant=original
for old,new in changes.items():
    assert variant.count(old)==1,old
    variant=variant.replace(old,new)
variant_path=HERE/'Runtime/VisualPoseEnvelope20Comparison.cs';write(variant_path,variant.encode())
trace_path=ROOT/'docs/p10/network/20260927T003126Z/probe.json';trace=json.loads(trace_path.read_text())
episodes=trace['correctionTrace']['episodes'];assert len(episodes)==39
def mode(e,side):return e['Presented'+side]['Pose']['Mode']
def bike_shift(e):
    a=e['PresentedBefore']['Pose'];b=e['PresentedAfter']['Pose']
    return math.hypot(a['BikeS']-b['BikeS'],a['BikeD']-b['BikeD'])
groups=[('largest-riding-to-falling',lambda e:mode(e,'Before')=='Riding' and mode(e,'After')=='Falling',lambda e:e['Delta']),
        ('largest-falling-to-riding',lambda e:mode(e,'Before')=='Falling' and mode(e,'After')=='Riding',lambda e:e['Delta']),
        ('same-falling-bike-step',lambda e:mode(e,'Before')==mode(e,'After')=='Falling',bike_shift),
        ('forecast-wrecked',lambda e:e['After']['Predicted']['Mode']==8,lambda e:e['Delta'])]
mode_ids={'Riding':0,'Attacking':1,'Hit':2,'Airborne':3,'Falling':4,'Detached':5,'Running':6,'Remounting':7,'Wrecked':8,'Busted':9,'Finished':10}
selected=[]
for identity,predicate,score in groups:
    index,e=max(((i,e) for i,e in enumerate(episodes) if predicate(e)),key=lambda value:score(value[1]))
    poses={}
    for side in ['Before','After']:
        recorded=e['Presented'+side]['Pose'];checkpoint=e[side]['Predicted']
        poses[side.lower()]={'s':recorded['S'],'d':recorded['D'],'h':recorded['H'],'bikeS':recorded['BikeS'],'bikeD':recorded['BikeD'],
            'bikeH':checkpoint['BikeHeightMillimeters']/1000,'speed':recorded['Speed'],'bikeSpeed':checkpoint['BikeSpeed']/1000,
            'lean':checkpoint['LeanMillidegrees']/1000,'mode':mode_ids[recorded['Mode']],'modeAge':recorded['ModeAge'],
            'attackSide':checkpoint['AttackSide'],'attackAge':checkpoint['AttackAgeTicks'],'kick':checkpoint['AttackWeapon']==3}
    selected.append({'id':identity,'originalIndex':index,'traceAt':e['At'],'rawPredictionCorrectionMeters':e['Delta'],
        'recordedPresentedDeltaMeters':e['PresentedDelta'],'course':e['Before']['Course'],'level':e['Before']['Level'],
        'authorityBeforeMode':e['Before']['Authority']['Mode'],'authorityAfterMode':e['After']['Authority']['Mode'],
        'forecastBeforeMode':e['Before']['Predicted']['Mode'],'forecastAfterMode':e['After']['Predicted']['Mode'],
        'sessionEpoch':e['Before']['SessionEpoch'],'raceEpoch':e['Before']['RaceEpoch'],'riderId':e['Before']['RiderId'],**poses})
assert len({r['originalIndex'] for r in selected})==4
fixture={'schema':1,'trace':trace_path.relative_to(ROOT).as_posix(),'traceSha256':sha(trace_path),'episodes':selected,
    'scope':'Four recorded presented pose pairs, not full WAN playback. Unfiltered target means input to the new visual envelope, not authoritative server position.',
    'reconstruction':'Bike height, lean and attack fields use the center full predictor checkpoint because the displayed-pose record omitted them. Pre-correction pose is held. After correction, constant captured speeds/height/lean and advancing mode age form an explicit diagnostic continuation. Camera history, ground visualization and colored reference obstacle/contact markers are constructed, not observed collision evidence. Forecast Wrecked retains its recorded rendered Falling mode.',
    'timing':'Target60Hz with real timestamps and missed-slot reporting; no synthetic backfilled observations. PNGs are explicit engine camera requests with asynchronous readback and deferred encoding, not desktop screenshots.'}
fixture_path=HERE/'Data/episodes.json';write(fixture_path,(json.dumps(fixture,indent=2)+'\n').encode())
record={'schema':1,'productionApplied':False,'unityCalled':False,'namespaceCopies':copies,
    'comparisonVariant':{'source':copies[0]['path'],'sourceSha256':copies[0]['sha256'],'path':variant_path.relative_to(ROOT).as_posix(),'sha256':sha(variant_path),'literalChanges':changes,'accepted':False},
    'fixture':{'path':fixture_path.relative_to(ROOT).as_posix(),'sha256':sha(fixture_path)},
    'frozenCandidateManifest':{'path':(BASE/'candidate-manifest.json').relative_to(ROOT).as_posix(),'sha256':sha(BASE/'candidate-manifest.json')}}
write(HERE/'prepared-inputs.json',(json.dumps(record,indent=2)+'\n').encode())
print(json.dumps({'namespaceCopies':len(copies),'cases':[(r['id'],r['originalIndex']) for r in selected],'fixtureSha256':sha(fixture_path),'liveEdits':False},indent=2))
