"""Verify source/player bytes before and after the owned native process. No raw logs are printed."""
from pathlib import Path
import argparse,datetime as dt,hashlib,json,subprocess,sys
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[3]
SETTINGS={'ProjectSettings/'+name+'.asset' for name in ('ProjectSettings','GraphicsSettings','QualitySettings')}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inside(root,relative):
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('receipt_path_outside_root')
    return path
def changed_files(root,rows):
    if not isinstance(rows,list) or not rows:raise ValueError('empty_file_manifest')
    changed=[];seen=set()
    for row in rows:
        path=inside(root,row['path'])
        if path in seen:raise ValueError('duplicate_manifest_path')
        seen.add(path)
        try:matches=path.is_file() and path.stat().st_size==row['bytes'] and digest(path)==row['sha256']
        except OSError:matches=False
        if not matches:changed.append(row['path'])
    return changed
def fingerprint(rows):
    return hashlib.sha256('\n'.join(row['path']+':'+row['sha256'] for row in rows).encode()).hexdigest()

def source_binding_changes(root,build,receipt):
    """Bind effective build settings separately from the exactly restored live originals."""
    rows=receipt['sources']
    if fingerprint(rows)!=receipt.get('sourceFingerprint'):raise ValueError('source_fingerprint_mismatch')
    changed=changed_files(root,rows)
    selected={row['path']:row for row in rows}
    modern=bool(SETTINGS.intersection(selected)) or 'sourcesAfter' in receipt or (build/'BuildEvidence/effective').exists()
    if not modern:
        return {'changedSources':changed,'settingsEvidenceIssues':[],'settingsBindingMode':'legacy_direct_live_sources','settingsEvidencePassed':None}
    if not SETTINGS.issubset(selected) or rows!=receipt.get('sourcesAfter') or receipt.get('changedDuringBuild')!=[]:
        raise ValueError('unchanged_complete_effective_settings_source_snapshots_required')
    changed=[path for path in changed if path not in SETTINGS]
    player_rows=receipt['playerFiles']
    if not isinstance(player_rows,list) or not player_rows:raise ValueError('empty_player_file_manifest')
    player={row['path']:row for row in player_rows}
    if len(player)!=len(player_rows):raise ValueError('duplicate_player_manifest_path')
    issues=[]
    def matches(path,row):
        try:return row is not None and path.is_file() and path.stat().st_size==row['bytes'] and digest(path)==row['sha256']
        except OSError:return False
    for name in sorted(SETTINGS):
        filename=Path(name).name
        for phase in ('effective','before','after'):
            relative='BuildEvidence/'+phase+'/'+filename
            path=inside(build,relative)
            if not matches(path,selected[name]):issues.append('effective_settings_mismatch:'+phase+'/'+filename)
            if not matches(path,player.get(relative)):issues.append('unbound_or_changed_settings_evidence:'+phase+'/'+filename)
        original_name='BuildEvidence/original/'+filename;restored_name='BuildEvidence/restored/'+filename
        original=inside(build,original_name);restored=inside(build,restored_name)
        original_row=player.get(original_name)
        if not matches(original,original_row):issues.append('unbound_or_changed_original_settings:'+filename)
        if not matches(restored,player.get(restored_name)):issues.append('unbound_or_changed_restored_settings:'+filename)
        if not matches(restored,original_row):issues.append('settings_restoration_mismatch:'+filename)
        if not matches(inside(root,name),original_row):changed.append(name)
    return {'changedSources':sorted(set(changed)),'settingsEvidenceIssues':issues,
            'settingsBindingMode':'effective_snapshots_and_restored_live_originals','settingsEvidencePassed':not issues}
def same_endpoint(a,b):
    try:
        x,y=urlsplit(a),urlsplit(b)
        return (x.scheme,x.hostname,x.port or 443,x.path,x.query,x.fragment)==(y.scheme,y.hostname,y.port or 443,y.path,y.query,y.fragment)
    except (TypeError,ValueError):return False
def final_verification(root,build,receipt,receipt_hash,payload,endpoint,exit_code):
    source_check=source_binding_changes(root,build,receipt)
    source_changes=source_check['changedSources'];player_changes=changed_files(build,receipt['playerFiles'])
    receipt_unchanged=digest(build/'NativeProbe.build.json')==receipt_hash
    runtime_ok=exit_code==0 and payload.get('status')=='PASS' and payload.get('sourceFingerprint')==receipt['sourceFingerprint'] and \
        payload.get('protocolVersion')==receipt['protocolVersion'] and payload.get('monoDetected') is True and \
        payload.get('platform')=='WindowsPlayer' and payload.get('backend')=='Mono2x' and same_endpoint(payload.get('endpoint'),endpoint)
    source_ok=not source_changes and not source_check['settingsEvidenceIssues']
    return {'status':'PASS' if runtime_ok and source_ok and not player_changes and receipt_unchanged else 'FAIL',
        'runtimeEvidencePassed':runtime_ok,'sourceStillMatches':source_ok,'playerFilesStillMatch':not player_changes,
        'buildReceiptStillMatches':receipt_unchanged,'changedPlayerFiles':player_changes,**source_check}
def stop_owned(process):
    if process is None or process.poll() is not None:return
    process.terminate()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',required=True,type=Path);parser.add_argument('--endpoint',required=True)
    parser.add_argument('--seconds',type=int,default=90);parser.add_argument('--report',required=True,type=Path)
    args=parser.parse_args(argv);endpoint=urlsplit(args.endpoint)
    if endpoint.scheme!='wss' or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment or endpoint.path!='/multiplayer':raise ValueError('ordinary_wss_endpoint_required')
    if not 60<=args.seconds<=600:raise ValueError('duration_out_of_bounds')
    build=args.build.resolve();report=args.report.resolve();allowed=(ROOT/'Build/NativeProbe').resolve()
    if build==allowed or not build.is_relative_to(allowed):raise ValueError('build_must_be_native_probe_child')
    if report.is_relative_to(build) or report.exists() or report.suffix!='.json':raise ValueError('fresh_json_report_outside_player_required')
    receipt_path=build/'NativeProbe.build.json';receipt=json.loads(receipt_path.read_text(encoding='utf-8-sig'))
    if not receipt.get('passed') or not receipt.get('sourceBindingPassed') or not receipt.get('editorStateRestored') or receipt.get('backend')!='Mono2x' or receipt.get('result')!='Succeeded' or receipt.get('errors',0)!=0 or receipt.get('failureCode'):raise ValueError('successful_restored_source_bound_build_required')
    if fingerprint(receipt['sources'])!=receipt['sourceFingerprint']:raise ValueError('source_fingerprint_mismatch')
    source_check=source_binding_changes(ROOT,build,receipt)
    if source_check['changedSources'] or source_check['settingsEvidenceIssues'] or changed_files(build,receipt['playerFiles']):raise ValueError('prelaunch_file_hash_mismatch')
    required={'RacingBoisNativeProbe.exe','UnityPlayer.dll','NativeProbe.binding.json'}
    if not required.issubset(row['path'] for row in receipt['playerFiles']):raise ValueError('required_player_files_unbound')
    binding=json.loads((build/'NativeProbe.binding.json').read_text(encoding='utf-8-sig'))
    if binding.get('sourceFingerprint')!=receipt['sourceFingerprint'] or binding.get('protocolVersion')!=receipt['protocolVersion']:raise ValueError('player_binding_mismatch')
    report.parent.mkdir(parents=True,exist_ok=True);launch=report.with_suffix('.launch.json');log=report.with_suffix('.player.log')
    if launch.exists() or log.exists() or Path(str(report)+'.tmp').exists():raise ValueError('fresh_report_log_prefix_required')
    record={'schema':2,'status':'PREPARING','startedUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'build':str(build),'buildReceiptSha256':digest(receipt_path),
        'sourceFingerprint':receipt['sourceFingerprint'],'protocolVersion':receipt['protocolVersion'],'endpoint':args.endpoint,'seconds':args.seconds,
        'settingsBindingMode':source_check['settingsBindingMode'],'settingsEvidencePassed':source_check['settingsEvidencePassed'],
        'scope':'Owned actual Unity Windows Mono process with before/after source/player hashes. No certificate bypass, gameplay override, raw log output or other-process control.'}
    with launch.open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2)
    command=[str(build/'RacingBoisNativeProbe.exe'),'-batchmode','-nographics','-logFile',str(log),'--rb-native-probe',
        '--rb-native-endpoint',args.endpoint,'--rb-native-report',str(report),'--rb-native-fingerprint',receipt['sourceFingerprint'],'--rb-native-seconds',str(args.seconds)]
    process=None;code=-1
    try:
        process=subprocess.Popen(command,cwd=build,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        record.update(ownedPid=process.pid,status='RUNNING');launch.write_text(json.dumps(record,indent=2),encoding='utf-8')
        code=process.wait(timeout=args.seconds+150)
    except subprocess.TimeoutExpired:record['errorCode']='owned_native_probe_timeout'
    except KeyboardInterrupt:record['errorCode']='launcher_interrupted'
    except Exception as error:record['errorCode']='launcher_'+type(error).__name__
    finally:stop_owned(process)
    payload={}
    try:
        if report.exists() and report.stat().st_size:payload=json.loads(report.read_text(encoding='utf-8-sig'))
        record.update(final_verification(ROOT,build,receipt,record['buildReceiptSha256'],payload,args.endpoint,code))
    except (OSError,ValueError,KeyError,TypeError) as error:record.update(status='FAIL',verificationError=type(error).__name__)
    record.update(completedUtc=dt.datetime.now(dt.timezone.utc).isoformat(),exitCode=code,runtimeReportSha256=digest(report) if report.is_file() else None)
    launch.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
    return 0 if record['status']=='PASS' else 1
