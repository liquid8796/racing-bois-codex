"""Generate the six-slot multiplayer table from exact source-bound authored locales."""
import hashlib
import json
from pathlib import Path
from template_rules import validate_template

HERE = Path(__file__).resolve().parent
raw = (HERE / 'canonical-source.json').read_bytes()
source = json.loads(raw)
source_sha = hashlib.sha256(raw).hexdigest()
keys = {entry['key'] for entry in source['entries']}
locales = {}
hashes = {}
for locale in ('ENU', 'DEU', 'ESP', 'FRA', 'ITA'):
    path = HERE / 'locales' / (locale + '.json')
    item = json.loads(path.read_text(encoding='utf8'))
    if item['locale'] != locale or item['sourceSha256'] != source_sha or set(item['entries']) != keys:
        raise ValueError('Locale/source coverage mismatch: ' + locale)
    locales[locale] = item['entries']; hashes[path.relative_to(HERE).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for entry in source['entries']:
        value = item['entries'][entry['key']]
        validate_template(value, entry['vi'])
lines = ['// Generated from source-bound authored locale files; no native UI acceptance.',
         'using System.Collections.Generic;', 'namespace RacingBois.Client.Application', '{', '    public static partial class UiText', '    {',
         '        static partial void AddMultiplayer(Dictionary<string, string[]> rows)', '        {']
for entry in source['entries']:
    values = [locales[locale][entry['key']] for locale in ('ENU', 'DEU', 'ESP', 'FRA', 'ITA')] + [entry['vi']]
    lines.append('            rows.Add(' + json.dumps(entry['key']) + ', new[] { ' + ', '.join(json.dumps(value, ensure_ascii=False) for value in values) + ' });')
lines += ['        }', '    }', '}']
target = HERE / 'UiText.Multiplayer.Generated.cs'
target.write_text('\n'.join(lines) + '\n', encoding='utf8')
report = dict(schema=1, sourceSha256=source_sha, sourceKeys=len(keys), localeOrder=['ENU','DEU','ESP','FRA','ITA','VI'],
              authoredTranslations=5*len(keys), compiledSlots=6*len(keys), localeHashes=hashes,
              generatedSha256=hashlib.sha256(target.read_bytes()).hexdigest(), placeholderSetsPassed=True, placeholderMultiplicitiesPassed=True,
              linguisticReviewComplete=False, nativeUiAccepted=False, visualAccepted=False)
(HERE / 'coverage.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(sourceKeys=len(keys), authoredTranslations=report['authoredTranslations'], compiledSlots=report['compiledSlots'])))
