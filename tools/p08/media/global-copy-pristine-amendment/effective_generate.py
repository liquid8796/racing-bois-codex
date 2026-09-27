"""Generate/check the explicitly reviewed Career overlay; never rewrite its frozen base."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = HERE.parent / 'global-copy-career-staging'
spec = importlib.util.spec_from_file_location('frozen_career_generator', BASE / 'generate.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
KEY = 'career.garage.pristine'
OLD, NEW = 'BIKE FULLY REPAIRED', 'BIKE UNDAMAGED'
COMMENT = '// Active inputs: tools/p08/media/global-copy-pristine-amendment/current-overlay.json (effective_generate.py).\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bound(row):
    path = ROOT / row['path']
    # Inputs must be checked-in source/data below tools, never ignored local backups.
    relative = path.resolve().relative_to((ROOT / 'tools/p08/media').resolve())
    if '..' in relative.parts or path.is_symlink() or sha(path.read_bytes()) != row['sha256']:
        raise ValueError('Bound input changed: ' + row['path'])
    return path


def one_cell(before, after):
    if set(before) != set(after):
        raise ValueError('Amendment key set changed')
    changes = [(key, before[key], after[key]) for key in before if before[key] != after[key]]
    if changes != [(KEY, OLD, NEW)]:
        raise ValueError('Expected only the reviewed pristine-state cell amendment')


def render(canonical, tables):
    text = ('// Generated from frozen complete Career translations. Do not hand-edit.\n'
            '// Provider order: ENU, DEU, ESP, FRA, ITA, VI.\n'
            'using System.Collections.Generic;\nnamespace RacingBois.Client.Application\n{\n'
            '    public static partial class UiText\n    {\n'
            '        static partial void AddCareer(Dictionary<string, string[]> rows)\n        {\n')
    for entry in canonical['entries']:
        key = entry['key']
        values = ', '.join(json.dumps(tables[locale][key], ensure_ascii=False) for locale in base.ORDER)
        text += '            rows.Add(' + json.dumps(key) + ', new[] { ' + values + ' });\n'
    return (text + '        }\n    }\n}\n').encode('utf-8')


def build(plan=None):
    plan = plan or base.load(HERE / 'current-overlay.json')
    if (plan.get('schema'), plan.get('revision'), plan.get('key'), plan.get('locale'), plan.get('before'), plan.get('after')) != (1, 2, KEY, 'ENU', OLD, NEW):
        raise ValueError('Unreviewed overlay identity')
    canonical = base.read_inventory()  # Exact canonical and original/reviewed installed view hashes.
    if bound(plan['canonical']) != BASE / 'canonical-source.json':
        raise ValueError('Unexpected canonical path')
    protected = base.load(bound(plan['protectedTokens']))
    if set(plan['locales']) != set(base.ORDER):
        raise ValueError('Incomplete locale inventory')
    tables = {}
    for locale in base.ORDER:
        expected = HERE / 'ENU.json' if locale == 'ENU' else BASE / ('VI.json' if locale == 'VI' else 'locales/' + locale + '.json')
        path = bound(plan['locales'][locale])
        if path != expected:
            raise ValueError('Unexpected active locale path: ' + locale)
        tables[locale] = base.validate_locale(base.load(path), locale, canonical, protected)
    prior_enu = base.validate_locale(base.load(bound(plan['baseEnu'])), 'ENU', canonical, protected)
    one_cell(prior_enu, tables['ENU'])
    old_tables = dict(tables, ENU=prior_enu)
    original = render(canonical, old_tables)
    if original != bound(plan['baseGenerated']).read_bytes():
        raise ValueError('Frozen baseline generated module no longer reproduces exactly')
    candidate = render(canonical, tables)
    if candidate != original.replace(json.dumps(OLD).encode(), json.dumps(NEW).encode(), 1):
        raise ValueError('More than the reviewed generated cell changed')
    candidate = candidate.replace(b'\n', b'\n' + COMMENT.encode(), 1)
    union = base.load(bound(plan['union']))
    prior_union = base.load(bound(plan['baseUnion']))
    before, after = {}, {}
    for source, target in ((prior_union, before), (union, after)):
        for locale, groups in source['texts'].items():
            for boundary, entries in groups.items():
                for key, value in entries.items():
                    target[(locale, boundary, key)] = value
    if set(before) != set(after) or len(after) != 5550:
        raise ValueError('Frozen union inventory changed')
    changed = [(key, before[key], after[key]) for key in before if before[key] != after[key]]
    if changed != [(('ENU', 'global', KEY), OLD, NEW)]:
        raise ValueError('Frozen union has an unreviewed difference')
    for locale in base.ORDER:
        for key, value in tables[locale].items():
            if after[(locale, 'global', key)] != value:
                raise ValueError('Effective copy differs from the reviewed native union')
    if plan['generated']['path'] != (HERE / 'UiText.Career.Generated.cs').relative_to(ROOT).as_posix() or sha(candidate) != plan['generated']['sha256']:
        raise ValueError('Effective generated output is not the reviewed revision')
    return candidate


def main():
    # The immutable revision2 build() remains available for historical controls.
    # Normal generation follows the reviewed active chain, including copy-fit fixes.
    current_path = HERE.parent / 'global-copy-effective/generate.py'
    current_spec = importlib.util.spec_from_file_location('active_global_copy', current_path)
    current = importlib.util.module_from_spec(current_spec)
    current_spec.loader.exec_module(current)
    return current.main()


def historical_revision2_main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify the staged output without writing it.')
    parser.add_argument('--check-live', action='store_true', help='Also require the installed production module to match.')
    args = parser.parse_args()
    candidate = build()
    output = HERE / 'UiText.Career.Generated.cs'
    if args.check or args.check_live:
        if output.read_bytes() != candidate:
            raise ValueError('Staged generated module differs from active inputs')
    else:
        temporary = output.with_name(output.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with temporary.open('xb') as stream:
                stream.write(candidate)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, output)
        finally:
            if temporary.exists():
                temporary.unlink()
    if args.check_live and (ROOT / 'Assets/RacingBois/Client/Application/UiText.Career.Generated.cs').read_bytes() != candidate:
        raise ValueError('Installed module differs from active reviewed output')
    print(json.dumps({'passed': True, 'revision': 2, 'generatedSha256': sha(candidate), 'careerCells': 906, 'unionCells': 5550, 'changedTranslationCells': 1, 'wroteProduction': False, 'checkedLive': args.check_live}))


if __name__ == '__main__':
    main()
