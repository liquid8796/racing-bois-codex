"""Verify by default; install only the exact reviewed diagnostic-preservation files."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
TARGETS = {
    'NativeProbe/NativeProbeBuilder.cs': 'NativeProbe/Editor/NativeProbeBuilder.cs',
    'NativeProbe/NativeProbeCompiledSources.cs': 'NativeProbe/Editor/NativeProbeCompiledSources.cs',
    'NativeProbe/RacingBois.Diagnostics.NativeProbe.Editor.asmdef': 'NativeProbe/Editor/RacingBois.Diagnostics.NativeProbe.Editor.asmdef',
    'PosePreview/PosePreviewBuilder.cs': 'PoseEnvelopePreview/Editor/PosePreviewBuilder.cs',
    'PosePreview/PreviewBuildInputs.cs': 'PoseEnvelopePreview/Editor/PreviewBuildInputs.cs',
    'PosePreview/RacingBois.Diagnostics.PoseEnvelopePreview.Editor.asmdef': 'PoseEnvelopePreview/Editor/RacingBois.Diagnostics.PoseEnvelopePreview.Editor.asmdef',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(path):
    for item in [path, *path.parents]:
        if item.exists() and (item.is_symlink() or item.is_junction()):
            raise ValueError('Linked installation/evidence path rejected')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    frozen = json.loads((HERE / 'handoff.json').read_text(encoding='utf8'))
    if frozen.get('schema') != 1 or len(frozen.get('files', [])) != len(TARGETS):
        raise ValueError('Unexpected staged target set')
    rows = {row['candidate']: row for row in frozen['files']}
    if len(rows) != len(TARGETS):
        raise ValueError('Duplicate staged candidates')
    checked = []
    for candidate, destination in TARGETS.items():
        source, target = HERE / candidate, ROOT / 'Assets/RacingBois/Diagnostics' / destination
        plain(source); plain(target)
        row = rows.get(source.relative_to(ROOT).as_posix())
        if row is None or row['destination'] != target.relative_to(ROOT).as_posix() or sha(source) != row['candidateSha256']:
            raise ValueError('Candidate or target binding changed')
        current = sha(target) if target.exists() else None
        if current not in {row['originalSha256'], row['candidateSha256']}:
            raise ValueError('Live diagnostic source changed independently: ' + destination)
        meta = Path(str(target) + '.meta'); plain(meta)
        if row['originalMetaSha256'] is not None and (not meta.exists() or sha(meta) != row['originalMetaSha256']):
            raise ValueError('Original script/asmdef metadata changed: ' + destination)
        if current is None and row['originalMetaSha256'] is None and meta.exists():
            raise ValueError('Unreviewed metadata exists for a new diagnostic source')
        checked.append((source, target, row))
    for helper in frozen['sharedHelpers']:
        path = ROOT / helper['path']; plain(path)
        if sha(path) != helper['sha256']:
            raise ValueError('Consumed shared helper changed: ' + helper['path'])
    audit = frozen['compileAuditSource']; plain(ROOT / audit['path'])
    if sha(ROOT / audit['path']) != audit['sha256']:
        raise ValueError('Compile-audit source changed')
    if args.install:
        validation = json.loads((HERE / 'validation.json').read_text(encoding='utf8'))
        if validation.get('managedCompilePassed') is not True or validation.get('independentReviewPassed') is not True or validation.get('handoffSha256') != sha(HERE / 'handoff.json'):
            raise ValueError('Review and managed validation must bind this exact handoff')
        # New proof helper and references arrive before builders using them.
        ordered = sorted(checked, key=lambda item: (0 if item[1].name == 'NativeProbeCompiledSources.cs' else 1 if item[1].suffix == '.asmdef' else 2, item[1].name))
        for source, target, row in ordered:
            if not target.exists() or sha(target) != row['candidateSha256']:
                shutil.copyfile(source, target)
        for _, target, row in checked:
            if sha(target) != row['candidateSha256']:
                raise ValueError('Installed source differs from reviewed candidate')
            if row['originalMetaSha256'] is not None and sha(Path(str(target) + '.meta')) != row['originalMetaSha256']:
                raise ValueError('Existing metadata changed during install')
    print(json.dumps({'checkedFiles': len(checked), 'installed': args.install, 'nativeVerified': False,
                      'next': 'Root refreshes Unity compilation and creates fresh compile proofs; native control/build still required.'}))


if __name__ == '__main__':
    main()
