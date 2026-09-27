"""Independently recompute native baseline measurements; never grants P08/release acceptance."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
from PIL import Image, __version__ as PILLOW_VERSION

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/p10'))
from package_desktop_candidate import canonical_path, digest, no_links

SETTINGS = {'ProjectSettings/' + name + '.asset' for name in ['ProjectSettings', 'GraphicsSettings', 'QualitySettings']}


def require(value, message):
    if not value:
        raise ValueError(message)


def file_at(root, relative):
    canonical_path(relative)
    path = root / relative
    no_links(path)
    require(path.is_file() and path.resolve().is_relative_to(root.resolve()), 'Bound file missing or escaped')
    return path


def verify_rows(root, rows):
    require(isinstance(rows, list) and rows, 'Missing file manifest')
    names = [row['path'] for row in rows]
    require(names == sorted(set(names)) and len(names) == len({name.casefold() for name in names}), 'File rows unordered/duplicated')
    for row in rows:
        path = file_at(root, row['path'])
        require(type(row['bytes']) is int and row['bytes'] >= 0 and path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], 'Bound bytes differ: ' + row['path'])


def build_audit(build_root, live_sources=True):
    build_root = build_root.resolve()
    build = json.loads((build_root / 'NativeBaseline.build.json').read_text(encoding='utf-8-sig'))
    require(build.get('passed') is True and build.get('sourceBindingPassed') is True and build.get('editorStateRestored') is True
            and build.get('result') == 'Succeeded' and build.get('target') == 'StandaloneWindows64' and build.get('backend') == 'Mono2x'
            and build.get('errors') == 0, 'Actual successful/restored native build required')
    rows = build['sources']
    require(rows == build.get('sourcesAfter') and build.get('changedDuringBuild') == [], 'Build source drift')
    names = [row['path'] for row in rows]
    require(names == sorted(set(names)), 'Build source set not canonical')
    fingerprint = hashlib.sha256('\n'.join(row['path'] + ' ' + row['sha256'] for row in rows).encode()).hexdigest()
    require(fingerprint == build['sourceFingerprint'], 'Build source fingerprint mismatch')
    if live_sources:
        verify_rows(ROOT, [row for row in rows if row['path'] not in SETTINGS])
    by_name = {row['path']: row for row in rows}
    for name in SETTINGS:
        row = by_name[name]
        for phase in ['effective', 'before', 'after']:
            path = build_root / 'BuildEvidence' / phase / Path(name).name
            require(path.is_file() and path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], 'Effective settings evidence mismatch')
        original = build_root / 'BuildEvidence/original' / Path(name).name
        restored = build_root / 'BuildEvidence/restored' / Path(name).name
        require(original.is_file() and restored.is_file() and digest(original) == digest(restored), 'Settings restoration evidence mismatch')
    verify_rows(build_root, build['playerFiles'])
    font_report = build.get('fontPreservationReport')
    require(isinstance(font_report, dict) and font_report.get('path') == (build_root / 'BuildEvidence/font-preservation.json').relative_to(ROOT).as_posix(), 'Font preservation summary must be bound to this build')
    verify_rows(ROOT, [font_report])
    fonts = json.loads((build_root / 'BuildEvidence/font-preservation.json').read_text())
    require(fonts.get('state') == 'restored' and fonts.get('globalSelection') is True and fonts.get('applied') is True
            and fonts.get('restored') is True and fonts.get('sourceBytesPreserved') is True and fonts.get('memoryAndAtlasPreserved') is True
            and fonts.get('failures') == [], 'Successful font preservation restoration required')
    for font in fonts.get('fonts', []):
        require(digest(file_at(ROOT, font['path'])) == font['sourceSha256'] and digest(file_at(ROOT, font['path'] + '.meta')) == font['metaSha256'], 'Protected font source/meta changed after build')
        private_backups = {font['sourceBackup'], font['metaBackup'], font['ownerMemoryBackup']}
        require(not any(row['path'] in private_backups or Path(row['path']).name in private_backups for row in build['playerFiles']), 'Private font backup must not be distributed')
    for name in ['RacingBoisNativeBaseline.exe', 'UnityPlayer.dll']:
        with file_at(build_root, name).open('rb') as stream:
            header = stream.read(64)
            require(len(header) == 64 and header[:2] == b'MZ', 'Native x64 PE header absent')
            offset = struct.unpack_from('<I', header, 60)[0]
            require(offset >= 64, 'Native PE offset invalid')
            stream.seek(offset); pe = stream.read(26)
            require(len(pe) == 26 and pe[:4] == b'PE\0\0' and struct.unpack_from('<H', pe, 4)[0] == 0x8664 and struct.unpack_from('<H', pe, 24)[0] == 0x20b, 'Actual native AMD64 PE32+ required')
    actual = {path.relative_to(build_root).as_posix() for path in build_root.rglob('*') if path.is_file() and path.name != 'NativeBaseline.build.json'}
    require(actual == {row['path'] for row in build['playerFiles']}, 'Unexpected/missing player files')
    binding = json.loads((build_root / 'NativeBaseline.binding.json').read_text())
    require(binding['sourceFingerprint'] == fingerprint and binding['seconds'] == 600 and binding['warmup'] == 10
            and binding['width'] == 1920 and binding['height'] == 1080 and binding['quality'] == 1
            and binding['targetFrameRate'] == -1 and binding['vSyncCount'] == 0, 'Native workload binding invalid')
    return build, binding


def number(row, key):
    value = float(row[key])
    require(math.isfinite(value), 'Nonfinite raw sample')
    return value


def measurements(frames, memory, workload, binding):
    require(len(frames) >= 600 and len(frames) <= 1000000, 'Insufficient or oversized native frame window')
    previous_time = 0.0
    previous = None
    delta = []
    expected_riders = 16 if binding['stress'] else 8
    quality_matches = True
    for index, frame in enumerate(frames):
        seconds, ms = number(frame, 'seconds'), number(frame, 'frame_ms')
        require(int(frame['index']) == index and seconds >= previous_time and (index == 0 or seconds > previous_time), 'Nonchronological frame observations')
        require(ms >= 0 and abs(ms - (seconds - previous_time) * 1000) < .001, 'Raw interval/time mismatch')
        require(int(frame['focused']) in {0, 1} and int(frame['measured_ticks']) >= 0 and int(frame['tick']) >= 0 and int(frame['cycle']) >= 0, 'Invalid frame state')
        require(index != 0 or int(frame['measured_ticks']) == 0, 'Measured simulation must start at zero')
        if previous is not None:
            require(int(frame['unity_frame']) == int(previous['unity_frame']) + 1, 'Missing or repeated Unity frame')
            require(0 <= int(frame['measured_ticks']) - int(previous['measured_ticks']) <= 6, 'Measured simulation step bound violated')
            require(0 <= int(frame['cycle']) - int(previous['cycle']) <= 1, 'Unexpected simulation cycle transition')
            require(int(frame['tick']) >= int(previous['tick']) or int(frame['cycle']) > int(previous['cycle']), 'World tick reset without cycle transition')
        for optional in ['cpu_ms', 'gpu_ms', 'gc_bytes']:
            if frame[optional] != '':
                require(number(frame, optional) >= 0, 'Negative optional counter')
        require(int(frame['timing_timestamp']) >= 0, 'Negative timing timestamp')
        quality_matches &= (int(frame['width']) == 1920 and int(frame['height']) == 1080 and int(frame['quality']) == 1
                            and int(frame['target_frame_rate']) == -1 and int(frame['vsync_count']) == 0 and int(frame['riders']) == expected_riders)
        if binding['stress']:
            quality_matches &= int(frame['traffic']) == 12 and int(frame['pedestrians']) == 6
        previous_time = seconds; previous = frame; delta.append(ms)
    elapsed = previous_time
    require(600 <= elapsed < 700, 'Native observation duration differs')
    require(workload['status'] == 'completed' and workload['editor'] is False and workload['requestedSampleSeconds'] == 600
            and workload['warmupSeconds'] == 10 and workload['frames'] == len(frames) - 1
            and workload['targetFrameRate'] == -1 and workload['vSyncCount'] == 0, 'Underlying workload window mismatch')
    require(workload['measuredSimulationTicks'] == int(frames[-1]['measured_ticks']) and workload['worldRestarts'] == int(frames[-1]['cycle']), 'Workload simulation counters differ')
    require(abs(workload['measuredSeconds'] - elapsed) <= max(delta) / 1000 + .01, 'Workload/observer clocks disagree')
    require(memory and len(memory) < 701, 'Memory observations missing/oversized')
    last = -1.0
    process_samples = []
    observed_times = {float(row['seconds']) for row in frames}
    for row in memory:
        seconds = number(row, 'seconds')
        require(last < seconds <= elapsed and (last < 0 or seconds - last >= 1 - .000001), 'Memory sample order/spacing invalid')
        require(seconds in observed_times, 'Memory timestamp has no observed frame')
        for name in ['working_set_bytes', 'private_bytes', 'unity_allocated_bytes', 'managed_bytes', 'graphics_driver_bytes']:
            if row[name] != '':
                require(number(row, name) >= 0, 'Negative memory counter')
        require((row['working_set_bytes'] == '') == (row['private_bytes'] == ''), 'Partial process memory sample')
        if row['working_set_bytes'] != '':
            require(int(row['working_set_bytes']) > 0 and int(row['private_bytes']) > 0 and int(row.get('process_error', '0')) == 0, 'Invalid process memory availability')
            process_samples.append((int(row['working_set_bytes']), int(row['private_bytes'])))
        elif 'process_error' in row:
            require(int(row['process_error']) != 0, 'Unavailable memory must retain its native error')
        last = seconds
    ordered = sorted(delta)
    p50 = ordered[math.ceil(len(delta) * .5) - 1]; p95 = ordered[math.ceil(len(delta) * .95) - 1]
    peak_working = max((row[0] for row in process_samples), default=0)
    peak_private = max((row[1] for row in process_samples), default=0)
    focused_seconds = sum(float(row['frame_ms']) for row in frames if int(row['focused'])) / 1000
    coverage = quality_matches and workload['measurementCoverageValid'] is True and workload['requiredDensityPresentEverySample'] is True
    coverage &= int(frames[-1]['measured_ticks']) / (elapsed * 60) >= .95
    coverage &= focused_seconds / elapsed >= .99
    memory_window = float(memory[0]['seconds']) <= float(frames[0]['seconds']) + .000001 and elapsed - float(memory[-1]['seconds']) <= 1 + max(delta) / 1000 + .001
    return {'frames': len(frames), 'measuredSeconds': elapsed, 'meanFps': len(frames) / elapsed,
            'p50Ms': p50, 'p95Ms': p95, 'maxMs': max(delta), 'peakWorkingSet': peak_working, 'peakPrivateBytes': peak_private,
            'workloadCoveragePassed': bool(coverage), 'timingBudgetPassed': len(frames) / elapsed >= 60 and p95 <= 20,
            'memoryBudgetPassed': memory_window and len(memory) >= 590 and len(process_samples) == len(memory) and 0 < peak_working <= 2 * 1024**3,
            'memorySamples': len(memory), 'processMemorySamples': len(process_samples),
            'focusedFrames': sum(int(row['focused']) for row in frames),
            'focusedSeconds': focused_seconds,
            'cpuTimingFrames': sum(row['cpu_ms'] != '' for row in frames), 'gpuTimingFrames': sum(row['gpu_ms'] != '' for row in frames),
            'gcFrames': sum(row['gc_bytes'] != '' for row in frames),
            'distinctTimingSamples': len({row['timing_timestamp'] for row in frames if int(row['timing_timestamp']) > 0}),
            'repeatedTimingFrames': sum(int(row['timing_timestamp']) > 0 for row in frames) - len({row['timing_timestamp'] for row in frames if int(row['timing_timestamp']) > 0})}


def audit(build_root, run):
    build, binding = build_audit(build_root)
    result = json.loads((run / 'receipt.json').read_text())
    require(result.get('completed') is True and result.get('status') == 'RECORDED_BASELINE' and result.get('identityStable') is True
            and result.get('releaseAccepted') is False and result.get('p08Accepted') is False, 'Incomplete or mis-scoped native observation')
    require(result['sourceFingerprint'] == build['sourceFingerprint'] and result['buildReceiptSha256'] == digest(build_root / 'NativeBaseline.build.json')
            and result['binding'] == binding and result['platform'] == 'WindowsPlayer' and result['graphicsApi'] == 'Direct3D11', 'Native build/runtime identity mismatch')
    require(result.get('processMemoryApi') == 'GetProcessMemoryInfo / PROCESS_MEMORY_COUNTERS_EX' and result.get('processMemoryStructureBytes') == 80
            and result.get('startupWorkingSet', 0) > 0 and result.get('startupPrivateBytes', 0) > 0 and result.get('startupMemoryError') == 0, 'Positive native Windows memory startup proof required')
    for field, name in [('rawSha256', 'frames.csv'), ('memorySha256', 'memory.csv'), ('workloadSha256', 'workload.json')]:
        require(digest(file_at(run, name)) == result[field], 'Raw observation bytes changed')
    frames = list(csv.DictReader((run / 'frames.csv').open(newline='', encoding='utf-8-sig')))
    memory = list(csv.DictReader((run / 'memory.csv').open(newline='', encoding='utf-8-sig')))
    workload = json.loads((run / 'workload.json').read_text())
    computed = measurements(frames, memory, workload, binding)
    require(result.get('memoryReadFailures') == sum(row['working_set_bytes'] == '' for row in memory), 'Native memory failure count differs')
    gpu_values = [float(row['gpu_ms']) for row in frames if row['gpu_ms']]
    computed['gpuCounterValuesExceedingEntireWindow'] = sum(value > computed['measuredSeconds'] * 1000 for value in gpu_values)
    computed['maximumRawGpuMilliseconds'] = max(gpu_values, default=None)
    computed['gpuCounterInterpretation'] = 'All raw values retained. Values exceeding the entire observation cannot represent a valid in-window GPU duration; no filtered GPU performance claim is made.'
    for name in ['frames', 'measuredSeconds', 'meanFps', 'p50Ms', 'p95Ms', 'maxMs', 'peakWorkingSet', 'peakPrivateBytes']:
        require(abs(computed[name] - result[name]) < .001, 'Native summary differs from raw samples: ' + name)
    for name in ['workloadCoveragePassed', 'timingBudgetPassed', 'memoryBudgetPassed']:
        require(computed[name] == result[name], 'Native gate differs from independently observed values: ' + name)
    require(result['routeMask'] == result['bikeMask'] == result['riderMask'] == 1, 'Baseline run changed available production masks')
    require({row['path'] for row in result['captures']} == {'warmup.png', 'completed.png'} and len(result['captures']) == 2, 'Native camera evidence incomplete')
    for row in result['captures']:
        path = file_at(run, row['path'])
        require(digest(path) == row['sha256'] and path.stat().st_size == row['bytes'], 'Native PNG binding differs')
        with Image.open(path) as png:
            png.verify()
        with Image.open(path) as png:
            png.load(); require(png.format == 'PNG' and png.size == (1920, 1080), 'Native PNG dimensions differ')
            extrema = png.convert('RGB').getextrema()
            require(any(hi - lo > 20 for lo, hi in extrema), 'Native camera pixels are uniform')
    start = dt.datetime.fromisoformat(result['startedUtc'].replace('Z', '+00:00'))
    end = dt.datetime.fromisoformat(result['finishedUtc'].replace('Z', '+00:00'))
    require(abs((end - start).total_seconds() - computed['measuredSeconds']) < .2, 'Native UTC/monotonic measurement window differs')
    computed.update(verified=True, measurementPassed=all(computed[name] for name in ['workloadCoveragePassed', 'timingBudgetPassed', 'memoryBudgetPassed']) and result['warnings'] == result['errors'] == 0,
                    warnings=result['warnings'], errors=result['errors'], releaseAccepted=False, p08Accepted=False,
                    receiptSha256=digest(run / 'receipt.json'), buildReceiptSha256=digest(build_root / 'NativeBaseline.build.json'),
                    verifierSha256=digest(Path(__file__)), pillowVersion=PILLOW_VERSION,
                    scope='Independent actual native baseline bytes/raw measurement verification only; P08, full-game, physical hardware matrix and release acceptance remain separate.')
    return computed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path); parser.add_argument('--run', required=True, type=Path); parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    require(not args.receipt.exists(), 'Verification receipt already exists')
    result = audit(args.build.resolve(), args.run.resolve())
    with args.receipt.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2); output.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
