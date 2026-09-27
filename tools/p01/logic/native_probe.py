"""Instrument a task-owned game copy before resuming it; never run the wrappers.

This is API containment for this known executable, not a security sandbox. Its
registry key is virtual, network/process launch are blocked, file mutations are
restricted to the copy. Display-mode changes are blocked. It records actual
native startup and any reachable ticks; it never calls that whole-game parity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import threading
import time
from native_project import SOURCE, OUT, EXPECTED_SHA256
import frida

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=int,default=20);ap.add_argument('--race',action='store_true');ap.add_argument('--scenario',choices=['crash','brake','steering','combat','hit','steal','police'],default='crash');args=ap.parse_args()
    assert 1<=args.seconds<=60
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED_SHA256
    workspace=Path(__file__).resolve().parent/'runtime-copy'
    workspace.mkdir(exist_ok=True)
    for path in SOURCE.parent.rglob('*'):
        rel=path.relative_to(SOURCE.parent)
        dest=workspace/rel
        if path.is_dir():dest.mkdir(exist_ok=True)
        elif path.suffix.lower() not in ['.bat','.reg']:
            if not dest.exists() or dest.stat().st_size!=path.stat().st_size:shutil.copy2(path,dest)
    exe=workspace/SOURCE.name
    assert hashlib.sha256(exe.read_bytes()).hexdigest()==EXPECTED_SHA256
    if (workspace/'ddraw.dll').exists():
        assert hashlib.sha256((workspace/'ddraw.dll').read_bytes()).hexdigest()=='85e0f7d530dfda134793a57cb3e76b0287dcc96892ee57162dd68f47283b03a9','Unrecognized local graphics wrapper'
        assert hashlib.sha256((workspace/'ddraw.ini').read_bytes()).hexdigest()=='f92aaf1074ea480965ec594ff1f59b415eb97047b9c645f6043e5dd0511c7528','Windowed wrapper configuration drift'
    before={str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.rglob('*') if p.is_file()}
    events=[];detached=threading.Event();ready=threading.Event()
    device=frida.get_local_device();pid=None;session=None
    result={'source_sha256':EXPECTED_SHA256,'kind':'instrumented native copied-process probe','frida_version':frida.__version__,'game_copy':str(workspace),'seconds_requested':args.seconds,'host_registry_mutation_authorized':False,'display_mode_mutation_authorized':False,'emulator':False}
    try:
        pid=device.spawn([str(exe)],cwd=str(workspace),stdio='pipe')
        result['owned_pid']=pid
        session=device.attach(pid)
        session.on('detached',lambda reason,crash:(events.append({'kind':'detached','reason':reason,'crash':str(crash) if crash else None}),detached.set()))
        script=device_script=Path(__file__).with_name('native_probe.js').read_text()
        script=script.replace('__COPY_PATH_JSON__',json.dumps(str(workspace))).replace('__RACE_PROBE__','true' if args.race else 'false').replace('__SCENARIO_JSON__',json.dumps(args.scenario))
        if args.scenario in ['hit','steal','police']:
            extension=Path(__file__).with_name('native_extended.js').read_text()
            script=script.replace("log('guards_ready'",extension+"\nlog('guards_ready'")
        result['loaded_instrumentation_sha256']=hashlib.sha256(script.encode()).hexdigest()
        result['harness_python_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        result['controlled_race_probe']=args.race
        result['scenario']=args.scenario
        agent=session.create_script(script)
        def message(msg,data):
            payload=msg.get('payload',{})
            if msg.get('type')=='send' and payload.get('kind')=='native_frame' and data:
                frames=OUT/'native-frames'/args.scenario;frames.mkdir(parents=True,exist_ok=True)
                stem='tick-%06d'%payload['tick']
                (frames/(stem+'.bin')).write_bytes(data)
                (frames/(stem+'.json')).write_text(json.dumps(payload,indent=2)+'\n')
                payload['binary_file']='native-frames/'+args.scenario+'/'+stem+'.bin'
            events.append(msg)
            if msg.get('type')=='send' and msg.get('payload',{}).get('kind')=='guards_ready':ready.set()
        agent.on('message',message);agent.load()
        if not ready.wait(10):raise RuntimeError('Instrumentation guards did not acknowledge ready; process will not resume')
        device.resume(pid)
        result['resumed']=True
        detached.wait(args.seconds)
        if not detached.is_set():
            result['status_before_terminate']=agent.exports_sync.snapshot()
    except Exception as exc:
        result['error']=type(exc).__name__+': '+str(exc)
    finally:
        if pid is not None:
            try:device.kill(pid);result['owned_process_terminated']=True
            except frida.ProcessNotFoundError:result['owned_process_already_exited']=True
            except Exception as exc:result['termination_error']=str(exc)
        if session:
            try:session.detach()
            except Exception:pass
    after={str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.rglob('*') if p.is_file()}
    result['copy_file_changes']=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
    result['original_executable_unchanged']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED_SHA256
    result['events']=events
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'native-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.race:(OUT/('native-probe-'+args.scenario+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    summary={k:v for k,v in result.items() if k not in ['events','status_before_terminate']}
    summary['runtime_counts']=result.get('status_before_terminate',{}).get('counts')
    summary['event_counts']={kind:sum(m.get('payload',{}).get('kind')==kind for m in events) for kind in ['native_state','native_frame','native_exception','blocked_registry_write','blocked_file_mutation']}
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
