"""Secret-free host preflight and real safe direct-MCP stage executor."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
STAGES = {
    'raw-import': 'import_raw()',
    'review-setup': 'prepare_review()',
    'reload-saved': 'reload_saved()',
    'saved-verification': 'verify_saved()',
    'rendered-checkpoint': 'finalize_review()',
    **{'render-' + name: 'render(' + repr(name) + ')'
       for name in ('quarter_positive', 'quarter_negative', 'side',
                    'axis_positive', 'axis_negative')},
    **{'render-clay-' + name: 'render(' + repr(name) + ", mode='clay')"
       for name in ('axis_positive', 'axis_negative')},
    **{'render-parts-id-' + name: 'render(' + repr(name) + ", mode='parts-id')"
       for name in ('quarter_positive', 'quarter_negative')},
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def bind(path: Path) -> dict:
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=STAGES)
    parser.add_argument('--port', type=int, default=9885)
    parser.add_argument('--config', type=Path, default=HERE / 'config.json')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise ValueError('Invalid owned Blender port')
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    candidate = (PROJECT / config['candidate_directory']).resolve()
    evidence = (PROJECT / config['evidence_directory']).resolve()
    if not candidate.is_relative_to(PROJECT / 'ArtSource/P08/Tripo'):
        raise ValueError('Candidate directory is outside the owned Tripo tree')
    if not evidence.is_relative_to(PROJECT / 'docs/p08/tripo'):
        raise ValueError('Evidence directory is outside the owned Tripo tree')
    locked = []
    for name in ('reference', 'input', 'protected_club'):
        path = PROJECT / config[name]['path']
        if sha(path) != config[name]['sha256']:
            raise ValueError('Locked/protected input changed: ' + name)
        locked.append(bind(path))
    model = candidate / config['model_name']
    if not args.prepare_only:
        with model.open('rb') as stream:
            if stream.read(4) != b'glTF':
                raise ValueError('Raw GLB not ready')
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'renders').mkdir(exist_ok=True)
    receipt = evidence / (args.stage + '-mcp.json')
    stage_report = evidence / (args.stage + '.json')
    if not args.prepare_only and (receipt.exists() or stage_report.exists()):
        raise ValueError('Existing stage evidence must be preserved and inspected')
    raw = candidate / config['raw_source_name']
    review = candidate / config['review_source_name']
    if not args.prepare_only:
        if args.stage == 'raw-import' and (raw.exists() or review.exists()):
            raise ValueError('Owned source already exists')
        if args.stage == 'review-setup' and review.exists():
            raise ValueError('Owned review source already exists')
        if args.stage == 'rendered-checkpoint' and review.with_name(review.stem + '_rendered.blend').exists():
            raise ValueError('Owned post-render checkpoint already exists')
        if args.stage.startswith('render-') and (evidence / 'renders' /
                                                 (args.stage[7:] + '.png')).exists():
            raise ValueError('Existing render must be preserved')
    config.update(candidate_absolute=candidate.as_posix(),
                  evidence_absolute=evidence.as_posix(),
                  requested_stage=args.stage, config_sha256=sha(config_path),
                  model_sha256=sha(model) if model.is_file() else None)
    # Literal preparation happens outside Blender; no exec/importlib, filesystem,
    # subprocess or network access is smuggled through its safe-mode validator.
    source = 'CONFIG = ' + repr(config) + '\n' + (HERE / 'review_support.py').read_text(
        encoding='utf-8') + '\n' + STAGES[args.stage] + '\n'
    code_dir = evidence / ('prepare-only-code' if args.prepare_only else 'prepared-code')
    code_dir.mkdir(exist_ok=True)
    code_path = code_dir / (args.stage + '.py')
    if code_path.exists() and code_path.read_text(encoding='utf-8') != source:
        if not args.prepare_only:
            raise ValueError('Prepared code differs; preserve and inspect its version')
    code_path.write_text(source, encoding='utf-8')
    if args.prepare_only:
        print(json.dumps({'prepared_only': True, 'stage': args.stage,
                          'code_path': str(code_path), 'source_sha256': sha(code_path)}))
        return 0
    before = {'locked_inputs': locked, 'model': bind(model),
              'raw': bind(raw) if raw.is_file() else None,
              'review': bind(review) if review.is_file() else None}
    preflight_path = evidence / (args.stage + '-preflight.json')
    with preflight_path.open('x', encoding='utf-8') as stream:
        json.dump(before, stream, indent=2)
        stream.write('\n')
    command = [str(PROJECT / '_local/blender-env/Scripts/python.exe'),
        str(PROJECT / 'tools/blender/mcp_client.py'), 'execute_blender_code',
        '--code-file', str(code_path), '--receipt', str(receipt), '--port', str(args.port),
        '--user-prompt', 'chúng ta có sự thay đổi 1 chút về flow tạo assets 3D, bây giờ sẽ bổ sung kết hợp blender vs tripo ai nhé. tiếp tục công việc dang dở nhé, update lun các assets cũ đã tạo bằng tripo ai lun cho đồng bộ.']
    stdout = evidence / (args.stage + '-stdout.log')
    stderr = evidence / (args.stage + '-stderr.log')
    with stdout.open('x', encoding='utf-8') as out, stderr.open('x', encoding='utf-8') as err:
        completed = subprocess.run(command, cwd=PROJECT, stdout=out, stderr=err,
                                   check=False, text=True, encoding='utf-8')
    preserved = all(sha(Path(b['path'])) == b['sha256'] for b in locked)
    preserved = preserved and sha(model) == before['model']['sha256']
    preserved = preserved and (not before['raw'] or sha(raw) == before['raw']['sha256'])
    preserved = preserved and (not before['review'] or sha(review) == before['review']['sha256'])
    if completed.returncode or not preserved:
        print(json.dumps({'stage': args.stage, 'process_exit_code': completed.returncode,
                          'input_and_saved_source_bytes_preserved': preserved,
                          'status': 'failed; inspect retained logs/receipt before retry'}))
        return 1
    payload = json.loads(receipt.read_text(encoding='utf-8'))
    marker = 'TRIPO_HQ_STAGE_JSON '
    reports = []
    for block in payload['result']['content']:
        if block.get('type') == 'text':
            for line in block.get('text', '').splitlines():
                if marker in line:
                    reports.append(json.loads(line.split(marker, 1)[1]))
    if len(reports) != 1 or reports[0]['stage'] != args.stage:
        raise RuntimeError('Missing or ambiguous actual Blender stage report')
    report = reports[0]
    report.update(host_verified_input_bytes_preserved=True,
                  host_model_binding=bind(model),
                  host_raw_source_binding=bind(raw) if raw.is_file() else None,
                  host_review_source_binding=bind(review) if review.is_file() else None,
                  host_prepared_code_binding=bind(code_path))
    if args.stage.startswith('render-'):
        report['host_render_binding'] = bind(Path(report['image_path']))
    if args.stage == 'rendered-checkpoint':
        report['host_rendered_source_binding'] = bind(Path(report['rendered_source_path']))
    with stage_report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'stage': args.stage, 'status': 'passed-with-scope',
                      'report': str(stage_report), 'visual_accepted': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
