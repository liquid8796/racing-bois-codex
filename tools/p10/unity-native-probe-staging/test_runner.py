"""Pure launcher evidence checks; fake files/process handles only, no native player/network execution."""
from pathlib import Path
import json,sys,uuid
import native_probe_runner as runner
ROOT=Path(__file__).resolve().parents[3]
private=(ROOT/'_local/native-probe-runner-tests'/uuid.uuid4().hex).resolve()
assert private.is_relative_to((ROOT/'_local/native-probe-runner-tests').resolve())
private.mkdir(parents=True);rows=[]
def test(name,operation):
    try:operation();rows.append({'name':name,'passed':True})
    except Exception as error:rows.append({'name':name,'passed':False,'error':type(error).__name__})
def check(value):
    if not value:raise AssertionError()
def fixture():
    root=private/uuid.uuid4().hex;build=root/'player';build.mkdir(parents=True);(root/'source.cs').write_text('source');(build/'player.dll').write_text('player')
    def row(path,parent):return {'path':path.relative_to(parent).as_posix(),'bytes':path.stat().st_size,'sha256':runner.digest(path)}
    receipt={'sourceFingerprint':'a'*64,'protocolVersion':6,'sources':[row(root/'source.cs',root)],'playerFiles':[row(build/'player.dll',build)]}
    path=build/'NativeProbe.build.json';path.write_text(json.dumps(receipt));sha=runner.digest(path)
    payload={'status':'PASS','sourceFingerprint':'a'*64,'protocolVersion':6,'monoDetected':True,'platform':'WindowsPlayer','backend':'Mono2x','endpoint':'wss://example.test/multiplayer'}
    return root,build,receipt,sha,payload
def final(values):return runner.final_verification(*values,'wss://example.test/multiplayer',0)
test('unchanged_before_after_native_evidence_can_pass',lambda:check(final(fixture())['status']=='PASS'))
def mutation(which):
    values=fixture();path=values[0]/'source.cs' if which=='source' else values[1]/'player.dll' if which=='player' else values[1]/'NativeProbe.build.json';path.write_text('modified-after-launch')
    result=final(values);check(result['status']=='FAIL');check(not result[{'source':'sourceStillMatches','player':'playerFilesStillMatch','receipt':'buildReceiptStillMatches'}[which]])
for kind in ['source','player','receipt']:test(kind+'_mutation_after_launch_fails',lambda k=kind:mutation(k))
def wrong_runtime():
    for key,value in [('protocolVersion',5),('platform','WindowsEditor'),('monoDetected',False),('endpoint','wss://other.test/multiplayer')]:
        values=fixture();values[4][key]=value;check(final(values)['status']=='FAIL')
test('wrong_protocol_runtime_or_endpoint_fails',wrong_runtime)
def reject_manifests():
    root,build,receipt,sha,payload=fixture()
    for entries in [[],receipt['sources']*2,[{'path':'../outside.cs','bytes':0,'sha256':'0'*64}]]:
        rejected=False
        try:runner.changed_files(root,entries)
        except ValueError:rejected=True
        check(rejected)
test('empty_duplicate_traversal_manifests_rejected',reject_manifests)
def process_scope():
    class Owned:
        def __init__(self,done=False):self.done=done;self.calls=[]
        def poll(self):return 0 if self.done else None
        def terminate(self):self.calls.append('terminate');self.done=True
        def wait(self,timeout):self.calls.append('wait');return 0
    owned=Owned();other=Owned();runner.stop_owned(owned);check(owned.calls==['terminate','wait'] and other.calls==[])
    ended=Owned(True);runner.stop_owned(ended);runner.stop_owned(None);check(ended.calls==[])
test('cleanup_controls_only_the_owned_live_handle',process_scope)
result={'passed':all(row['passed'] for row in rows),'tests':len(rows),'results':rows,'scope':'Pure launcher helpers with private fake files/owned fake process handles. No network, native player, source edit or real process termination.'}
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'tests':len(rows)}));raise SystemExit(0 if result['passed'] else 1)
