"""Compose reviewed keyed copy amendments over an immutable six-locale baseline."""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
POINTER = HERE / 'current.json'
LOCALES = ['ENU', 'DEU', 'ESP', 'FRA', 'ITA', 'VI']
ROW = re.compile(r'^(\s*)rows\.Add\(("(?:\\.|[^"\\])*"), new\[\] \{ (.*) \}\);$')
SLOT = re.compile(r'\{([A-Za-z][A-Za-z0-9]*)\}')
COMMENT = '// Active inputs: tools/p08/media/global-copy-effective/current.json; regenerate with global-copy-effective/generate.py.'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)


def file(relative):
    if not isinstance(relative, str) or '\\' in relative or ':' in relative or any(part in {'', '.', '..'} for part in relative.split('/')):
        raise ValueError('Canonical repository-relative path required')
    path = ROOT / relative
    path.resolve().relative_to(ROOT.resolve())
    if any(item.is_symlink() or getattr(item, 'is_junction', lambda: False)() for item in [path, *path.parents] if item != ROOT and ROOT in item.parents):
        raise ValueError('Linked input/output rejected')
    return path


def bound(row):
    path = file(row['path'])
    data = path.read_bytes()
    if digest(data) != row['sha256']:
        raise ValueError('Reviewed bytes changed: ' + row['path'])
    return path


def arguments(value):
    if not isinstance(value, str) or not value.strip() or '\ufffd' in value or any(ord(c) < 32 and c != '\n' for c in value):
        raise ValueError('Invalid authored copy')
    residue = SLOT.sub('', value)
    if '{' in residue or '}' in residue:
        raise ValueError('Malformed template argument')
    return Counter(SLOT.findall(value))


def table(source):
    result = {}
    for line in source.splitlines():
        match = ROW.fullmatch(line)
        if match is None:
            continue
        key = json.loads(match[2])
        values = json.loads('[' + match[3] + ']')
        if key in result or len(values) != len(LOCALES) or any(not isinstance(value, str) for value in values):
            raise ValueError('Malformed generated table: ' + key)
        result[key] = values
    return result


def compose(plan):
    if plan.get('schema') != 1 or plan.get('scope') != 'reviewed-copy-fit-amendment' or plan.get('nativeUiAccepted') is not False:
        raise ValueError('Explicit unaccepted copy-fit amendment required')
    base_union = load(bound(plan['baseUnion']))
    if base_union.get('localeOrder') != LOCALES or base_union.get('globalKeys') != 394 or base_union.get('cinematicKeys') != 531:
        raise ValueError('Wrong frozen copy baseline')
    union = copy.deepcopy(base_union)
    module_sources, module_tables, owners = {}, {}, {}
    for module in plan['modules']:
        name = module['name']
        if name not in {'Main', 'Career', 'Multiplayer', 'ClientMessages'} or name in module_sources:
            raise ValueError('Unknown/duplicate copy provider')
        source = bound(module['base']).read_text(encoding='utf-8')
        rows = table(source)
        for key, values in rows.items():
            if key in owners:
                raise ValueError('Semantic key belongs to multiple providers')
            owners[key] = name
            for locale, value in zip(LOCALES, values):
                if base_union['texts'][locale]['global'].get(key) != value:
                    raise ValueError('Baseline module differs from frozen authored union')
        module_sources[name] = source
        module_tables[name] = rows
    if set(module_sources) != {'Main', 'Career', 'Multiplayer', 'ClientMessages'} or len(owners) != 394:
        raise ValueError('Incomplete baseline copy providers')
    if set(base_union.get('texts', {})) != set(LOCALES):
        raise ValueError('Frozen union locale inventory differs')
    cinematic_keys = set(base_union['texts']['ENU']['cinematic'])
    if len(cinematic_keys) != 531:
        raise ValueError('Frozen cinematic key inventory differs')
    for locale in LOCALES:
        if set(base_union['texts'][locale]) != {'global', 'cinematic'} or set(base_union['texts'][locale]['global']) != set(owners) or set(base_union['texts'][locale]['cinematic']) != cinematic_keys:
            raise ValueError('Frozen union key coverage differs')
    changes = plan.get('changes')
    if not isinstance(changes, list) or not changes:
        raise ValueError('No explicit authored amendment cells')
    if load(bound(plan['authoredChanges'])) != changes:
        raise ValueError('Observed authored findings differ from the reviewed plan')
    seen, changed_modules = set(), set()
    for change in changes:
        key, locale, module = change['key'], change['locale'], change['provider']
        identity = (locale, key)
        if identity in seen or owners.get(key) != module or locale not in LOCALES or locale == 'VI':
            raise ValueError('Duplicate/unowned amendment or frozen VI source change')
        seen.add(identity)
        before, after = change['before'], change['after']
        if base_union['texts'][locale]['global'][key] != before or before == after:
            raise ValueError('Amendment does not match its exact prior cell')
        if arguments(before) != arguments(after) or before.count('\n') != after.count('\n') or before.count('$') != after.count('$'):
            raise ValueError('Amendment changed template arguments, explicit breaks or currency')
        if not isinstance(change.get('reason'), str) or not change['reason'].strip() or not change.get('evidence'):
            raise ValueError('Observed reason/evidence required')
        for evidence in change['evidence']:
            bound(evidence)
        for token in change.get('protectedTokens', []):
            if before.count(token) != after.count(token):
                raise ValueError('Protected token changed')
        union['texts'][locale]['global'][key] = after
        module_tables[module][key][LOCALES.index(locale)] = after
        changed_modules.add(module)
    output = {}
    for module in plan['modules']:
        name = module['name']
        if name not in changed_modules:
            continue
        lines = []
        for line in module_sources[name].splitlines():
            match = ROW.fullmatch(line)
            if match and any(key == json.loads(match[2]) for _, key in seen):
                key = json.loads(match[2])
                values = ', '.join(json.dumps(value, ensure_ascii=name in {'Main', 'ClientMessages'}) for value in module_tables[name][key])
                line = match[1] + 'rows.Add(' + match[2] + ', new[] { ' + values + ' });'
            if not line.startswith('// Active inputs:'):
                lines.append(line)
        lines.insert(1, COMMENT)
        output[name] = ('\n'.join(lines) + '\n').encode('utf-8')
    union['scope'] = 'Authored effective text union after observed copy-fit amendments; native rerender/readability acceptance remains separate'
    union['inputs'] = [plan['baseUnion'], plan['authoredChanges']] + [module['base'] for module in plan['modules']]
    union['amendmentChain'] = {'baseUnion': plan['baseUnion'], 'amendment': plan['identity'], 'changedCells': len(seen)}
    effective = {locale: {'schema': 1, 'locale': locale, 'boundary': 'global-effective', 'strings': union['texts'][locale]['global'], 'nativeUiAccepted': False} for locale in LOCALES}
    return output, union, effective


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--check-live', action='store_true')
    args = parser.parse_args(argv)
    pointer = load(POINTER)
    if pointer.get('schema') != 1:
        raise ValueError('Active overlay pointer schema differs')
    plan_path = bound(pointer['active'])
    plan = load(plan_path)
    outputs, union, effective = compose(plan)
    destination = file(pointer['outputDirectory'])
    if destination != plan_path.parent:
        raise ValueError('Outputs must remain in the reviewed amendment folder')
    expected = {destination / ('UiText.' + name + '.Generated.cs'): data for name, data in outputs.items()}
    expected[destination / 'authored-text-union.json'] = (json.dumps(union, ensure_ascii=False, indent=2) + '\n').encode()
    for locale, catalog in effective.items():
        expected[destination / 'locales' / (locale + '.json')] = (json.dumps(catalog, ensure_ascii=False, indent=2) + '\n').encode()
    for path, data in expected.items():
        if args.check or args.check_live:
            if path.read_bytes() != data:
                raise ValueError('Effective generated artifact differs: ' + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if args.check_live:
        for name, data in outputs.items():
            if file('Assets/RacingBois/Client/Application/UiText.' + name + '.Generated.cs').read_bytes() != data:
                raise ValueError('Installed copy module differs: ' + name)
    print(json.dumps({'passed': True, 'changedCells': len(plan['changes']), 'changedProviders': sorted(outputs), 'artifacts': len(expected), 'wroteProduction': False, 'nativeUiAccepted': False}))


if __name__ == '__main__':
    main()
