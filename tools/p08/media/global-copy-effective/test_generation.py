"""Focused active-chain controls; mutate only in-memory plans, never authored files."""
import copy
import json
from unittest.mock import patch
import generate as active

pointer = active.load(active.POINTER)
plan = active.load(active.bound(pointer['active']))
output, union, catalogs = active.compose(plan)
assert set(output) == {row['provider'] for row in plan['changes']} and len(catalogs) == 6
assert union['texts']['ENU']['global']['career.garage.pristine'] == 'BIKE UNDAMAGED'
baseline = active.load(active.bound(plan['baseUnion']))
actual_changes = {(locale, group, key): value for locale, groups in union['texts'].items() for group, values in groups.items()
                  for key, value in values.items() if value != baseline['texts'][locale][group][key]}
assert actual_changes == {(row['locale'], 'global', row['key']): row['after'] for row in plan['changes']}
checks = ['exact_authored_provider_and_cells', 'prior_english_amendment_retained']


def rejected(name, mutate):
    modified = copy.deepcopy(plan)
    mutate(modified)
    original_load = active.load
    def read(path):
        if path == active.file(plan['authoredChanges']['path']):
            return modified['changes']
        return original_load(path)
    try:
        with patch.object(active, 'load', side_effect=read):
            active.compose(modified)
    except (ValueError, KeyError):
        checks.append(name)
    else:
        raise AssertionError('Invalid plan accepted: ' + name)


for name, mutate in [
    ('stale_base_union', lambda p: p['baseUnion'].update(sha256='0' * 64)),
    ('stale_base_module', lambda p: p['modules'][0]['base'].update(sha256='0' * 64)),
    ('duplicate_cell', lambda p: p['changes'].append(copy.deepcopy(p['changes'][0]))),
    ('wrong_prior_value', lambda p: p['changes'][0].update(before='different')),
    ('unknown_semantic_key', lambda p: p['changes'][0].update(key='unreviewed.key')),
    ('wrong_provider', lambda p: p['changes'][0].update(provider='Main')),
    ('frozen_vi_cannot_change', lambda p: p['changes'][0].update(locale='VI')),
    ('extra_argument', lambda p: p['changes'][0].update(after='Intact {bike}')),
    ('malformed_argument', lambda p: p['changes'][0].update(after='Intact {')),
    ('changed_linebreak', lambda p: p['changes'][0].update(after='Intact\n')),
    ('changed_currency', lambda p: p['changes'][0].update(after='Intact $')),
    ('missing_evidence', lambda p: p['changes'][0].update(evidence=[])),
    ('stale_render_evidence', lambda p: p['changes'][0]['evidence'][0].update(sha256='0' * 64)),
]:
    rejected(name, mutate)
allowed = set(active.load(active.ROOT / 'docs/p08/media/global-copy-character-corpus-20260928.json')['codepoints'])
needed = {ord(c) for locale in union['texts'].values() for group in locale.values() for text in group.values() for c in text + text.upper() if ord(c) >= 32}
assert needed <= allowed
checks.append('effective_text_covered_by_existing_owned_font_corpus')
print(json.dumps({'passed': True, 'controls': len(checks), 'cases': checks, 'nativeUiAccepted': False}))
