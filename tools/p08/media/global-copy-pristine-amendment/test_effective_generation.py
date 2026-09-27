"""Focused in-memory controls; do not change frozen authored inputs or production."""
import copy
import json
from unittest.mock import patch
import effective_generate as active

plan = active.base.load(active.HERE / 'current-overlay.json')
expected = (active.HERE / 'UiText.Career.Generated.cs').read_bytes()
assert active.build(plan) == expected
revision1 = (active.HERE / 'revision1/UiText.Career.Generated.cs').read_bytes()
assert expected == revision1.replace(b'\n', b'\n' + active.COMMENT.encode(), 1)
checks = ['exact_active_generation', 'comment_only_vs_native_revision1']


def rejects(name, action):
    try:
        action()
    except ValueError:
        checks.append(name)
    else:
        raise AssertionError('Invalid overlay accepted: ' + name)


rejects('legacy_entry_cannot_revert', active.base.generate)
for name, mutate in [
    ('wrong_revision', lambda p: p.update(revision=1)),
    ('stale_locale_hash', lambda p: p['locales']['ENU'].update(sha256='0' * 64)),
    ('missing_locale', lambda p: p['locales'].pop('FRA')),
    ('stale_output_hash', lambda p: p['generated'].update(sha256='0' * 64)),
    ('stale_union_hash', lambda p: p['union'].update(sha256='0' * 64)),
]:
    altered = copy.deepcopy(plan)
    mutate(altered)
    rejects(name, lambda: active.build(altered))
rejects('no_amendment', lambda: active.one_cell({active.KEY: active.OLD}, {active.KEY: active.OLD}))
rejects('second_changed_cell', lambda: active.one_cell({active.KEY: active.OLD, 'other': 'x'}, {active.KEY: active.NEW, 'other': 'y'}))
rejects('extra_key', lambda: active.one_cell({active.KEY: active.OLD}, {active.KEY: active.NEW, 'extra': 'x'}))
with patch.object(active.base, 'digest', return_value='0' * 64):
    rejects('canonical_source_drift', active.build)
print(json.dumps({'passed': True, 'controls': len(checks), 'cases': checks, 'wroteProduction': False}))
