"""Combine completed measurements, never turn an unfinished run into a passing phase."""
import argparse,datetime,hashlib,json,pathlib
from package import sources
root=pathlib.Path(__file__).resolve().parents[2];docs=root/'docs/p09'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--release',default='p09-20260927-c')
parser.add_argument('--network-run',default='20260926T175901Z')
parser.add_argument('--before',default='docs/p09/network-health-after-90s.json')
parser.add_argument('--after',default='docs/p09/network-health-after-30m.json')
parser.add_argument('--observer',default='docs/p09/soak-observer.json')
parser.add_argument('--output',default='docs/p09/capacity.json')
parser.add_argument('--maintenance-event',default='')
arguments=parser.parse_args()
def read(relative):return json.loads((root/relative).read_text(encoding='utf-8-sig'))
release=read('Build/OciStaging/'+arguments.release+'/release.json')
if sources()!=release['source']:raise RuntimeError('Backend source changed after the selected release')
run=read('docs/p10/network/'+arguments.network_run+'/run.json');probe=read('docs/p10/network/'+arguments.network_run+'/probe.json')
if run['status']!='PASS' or probe['status']!='PASS':raise RuntimeError('WSS soak has not passed')
before=read(arguments.before)['multiplayer'];after=read(arguments.after)['multiplayer']
hist=after['tickDurationHistogram'];counts=[a-b for a,b in zip(hist['bucketCounts'],before['tickDurationHistogram']['bucketCounts'])]
if min(counts)<0:raise RuntimeError('Server restarted; histogram delta cannot be compared')
count=sum(counts)
def percentile(fraction):
    accumulated=0
    for upper,value in zip(hist['bucketUpperBoundsMilliseconds'],counts):
        accumulated+=value
        if accumulated>=count*fraction:return upper
observer=read(arguments.observer);samples=[s for s in observer['samples'] if s['sshSucceeded']]
first,last=samples[0],samples[-1]
observed_seconds=(datetime.datetime.fromisoformat(last['utc'])-datetime.datetime.fromisoformat(first['utc'])).total_seconds()
cpu_cores=(last['service']['CPUUsageNSec']-first['service']['CPUUsageNSec'])/1e9/observed_seconds
clients=[{'index':i,'meanRttMilliseconds':c['MeanRtt'],'maximumRttMilliseconds':c['MaximumRtt'],
          'averageUploadBytesPerSecondWholeRun':c['SentBytes']/probe['elapsedSeconds'],
          'averageDownloadBytesPerSecondWholeRun':c['ReceivedBytes']/probe['elapsedSeconds'],
          'invalidSnapshots':c['InvalidSnapshots'],'maximumCorrectionMeters':c['MaximumCorrection']} for i,c in enumerate(probe['clients'])]
report={'schemaVersion':1,'generatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed_for_measured_staging_scope',
        'releaseId':release['releaseId'],'sourceSha256':release['source']['sha256'],'sourceStillMatches':True,
        'networkRun':run['runId'],'elapsedSeconds':probe['elapsedSeconds'],'peers':probe['peers'],'raceCycles':probe['cycles'],
        'intentionalReconnects':probe['reconnects'],'reconnectStorms':probe['storms'],'clients':clients,
        'serverWorkload':{'tickSamples':count,'p50UpperBoundMilliseconds':percentile(.50),'p95UpperBoundMilliseconds':percentile(.95),'p99UpperBoundMilliseconds':percentile(.99),
          'slowTicksDelta':after['slowTicks']-before['slowTicks'],'droppedCatchupTicksDelta':after['droppedCatchupTicks']-before['droppedCatchupTicks'],
          'persistenceFailuresDelta':after['persistenceFailures']-before['persistenceFailures'],'lifetimeMaximumStepMilliseconds':after['maximumStepMilliseconds']},
        'resourceObservation':{'firstUtc':first['utc'],'lastUtc':last['utc'],'observedSeconds':observed_seconds,'samples':len(samples),
          'averageCpuCores':cpu_cores,'maximumObservedCgroupMemoryBytes':max(s['service']['MemoryCurrent'] for s in samples),
          'firstCgroupMemoryBytes':first['service']['MemoryCurrent'],'lastCgroupMemoryBytes':last['service']['MemoryCurrent'],
          'serviceAutomaticRestartsDelta':last['service']['NRestarts']-first['service']['NRestarts']},
        'maintenanceEvent':arguments.maintenance_event or None,
        'limits':'One eight-client room from one Windows Internet origin to Frankfurt. Includes planned reconnects. Any maintenance during the run is recorded separately. No claim for 16 players, eight simultaneous rooms, large account population, Unity client visuals/FPS, eight-hour duration or global player feel.',
        'fullP09PhaseComplete':False,'openGates':['Rendered Unity Windows client against OCI','Real multiplayer clients in multiple regions','Final approved P08 assets published','Production domain/notification/key-escrow decisions']}
out=root/arguments.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2))
print(json.dumps({'status':report['status'],'ticks':count,'p99UpperBoundMilliseconds':percentile(.99),'averageCpuCores':cpu_cores,'sourceStillMatches':True},indent=2))
