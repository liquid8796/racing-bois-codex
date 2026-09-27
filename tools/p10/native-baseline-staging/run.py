"""Own one actual graphics-enabled Windows baseline player and verify its bytes."""
from pathlib import Path
import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from verify import ROOT, audit, build_audit, digest, no_links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    no_links(args.build); no_links(args.output)
    build_root, output = args.build.resolve(), args.output.resolve()
    if not build_root.is_relative_to(ROOT / 'Build/NativeBaseline') or not output.is_relative_to(ROOT / 'docs/p10/native-baseline') or output.exists():
        raise ValueError('New owned build/output children required')
    build, binding = build_audit(build_root)
    build_hash = digest(build_root / 'NativeBaseline.build.json')
    output.mkdir(parents=True, exist_ok=False)
    runtime = output / 'runtime'
    receipt = output / 'launch.json'
    result = {'schema': 1, 'state': 'PREPARED', 'startedUtc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'build': build_root.relative_to(ROOT).as_posix(), 'output': output.relative_to(ROOT).as_posix(),
              'sourceFingerprint': build['sourceFingerprint'], 'buildReceiptSha256': build_hash,
              'launcherSha256': digest(Path(__file__)), 'releaseAccepted': False, 'p08Accepted': False,
              'scope': 'Owned graphics-enabled native P06 baseline diagnostic; all selected build/source bytes checked before/after. Not final game acceptance.'}
    def save():
        receipt.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    save()
    command = [str(build_root / 'RacingBoisNativeBaseline.exe'), '-force-d3d11', '-screen-fullscreen', '0', '-screen-width', '1920', '-screen-height', '1080',
               '-logFile', str(output / 'player.log'), '--rb-baseline-output', str(runtime),
               '--rb-baseline-buildsha', build_hash, '--rb-baseline-fingerprint', build['sourceFingerprint']]
    process = None
    try:
        # No -batchmode/-nographics: this run measures the actual native graphics path.
        process = subprocess.Popen(command, cwd=build_root, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        result.update(state='RUNNING', ownedPid=process.pid); save()
        print(json.dumps({'state': 'RUNNING', 'pid': process.pid, 'receipt': str(receipt)}), flush=True)
        deadline = time.monotonic() + 750
        while process.poll() is None:
            if time.monotonic() > deadline:
                raise TimeoutError('owned_baseline_watchdog')
            time.sleep(.5)
        result['exitCode'] = process.returncode
        result['allPlayerAndSourceBytesStillMatch'] = False
        build_audit(build_root)
        if digest(build_root / 'NativeBaseline.build.json') != build_hash:
            raise ValueError('Build receipt changed during observation')
        result['allPlayerAndSourceBytesStillMatch'] = True
        if process.returncode != 0:
            raise ValueError('Native baseline player did not exit successfully')
        verified = audit(build_root, runtime)
        (output / 'verification.json').write_text(json.dumps(verified, indent=2)+'\n', encoding='utf-8')
        result.update(state='VERIFIED_BASELINE', measurementPassed=verified['measurementPassed'],
                      verificationSha256=digest(output / 'verification.json'))
    except Exception as error:
        result.update(state='FAIL', errorCode=str(error) if isinstance(error, (ValueError, TimeoutError)) else type(error).__name__)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=10)
        result['ownedProcessStopped'] = process is None or process.poll() is not None
        result['finishedUtc'] = dt.datetime.now(dt.timezone.utc).isoformat(); save()
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result['state'] == 'VERIFIED_BASELINE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
