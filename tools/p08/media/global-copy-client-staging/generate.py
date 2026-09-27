"""Generate scoped client-status display copy; do not edit any production source."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LOCALES = ('VI', 'ENU', 'DEU', 'ESP', 'FRA', 'ITA')
ORDER = ('ENU', 'DEU', 'ESP', 'FRA', 'ITA', 'VI')


def load_rows():
    canonical_bytes = (HERE / 'canonical-source.json').read_bytes()
    canonical = json.loads(canonical_bytes)
    freeze = json.loads((HERE / 'templates-freeze.json').read_text(encoding='utf-8'))
    if hashlib.sha256(canonical_bytes).hexdigest() != freeze['canonicalSourceSha256']:
        raise ValueError('Frozen canonical source changed')
    for name, allowed in freeze['approvedLiveSourceHashes'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() not in allowed:
            raise ValueError('Unreviewed live source revision: ' + name)
    result = {}
    source_values = set()
    for line in (HERE / 'author-client.tsv').read_text(encoding='utf-8').splitlines():
        key, *values = line.split('\t')
        if len(values) != len(LOCALES) or key in result or not re.fullmatch(r'(?:client|content)\.[a-z_]+(?:\.[a-z_]+)*', key):
            raise ValueError('Malformed or duplicate client message key: ' + key)
        if values[0] in source_values or any(not v.strip() for v in values):
            raise ValueError('Duplicate source or empty translation: ' + key)
        expected = {'route'} if key == 'content.route.loading' else set()
        for value in values:
            slots = set(re.findall(r'\{([a-z]+)\}', value))
            remainder = re.sub(r'\{[a-z]+\}', '', value)
            if slots != expected or '{' in remainder or '}' in remainder:
                raise ValueError('Changed template arguments: ' + key)
        source_values.add(values[0])
        result[key] = dict(zip(LOCALES, values))
    if len(result) != 34:
        raise ValueError('Expected 34 reviewed whole client/status messages')
    if {key: row['VI'] for key, row in result.items()} != {row['key']: row['vi'] for row in canonical['entries']}:
        raise ValueError('Author worksheet no longer matches the canonical source')
    return result


def main():
    rows = load_rows()
    q = lambda value: json.dumps(value, ensure_ascii=True)
    code = ['// Generated from author-client.tsv. Scoped display copy only.',
            'using System.Collections.Generic;', 'using RacingBois.Gameplay.Definitions;',
            'namespace RacingBois.Client.Application', '{', '    public static partial class UiText', '    {',
            '        static partial void AddClientMessages(Dictionary<string, string[]> rows)', '        {']
    for key, values in rows.items():
        code.append('            rows.Add(' + q(key) + ', new[] { ' + ', '.join(q(values[lang]) for lang in ORDER) + ' });')
    code += ['        }', '        static partial void TranslateClientMessage(string locale, string raw, ref string translated)',
             '        {', '            switch (raw)', '            {']
    for key, values in rows.items():
        if key != 'content.route.loading':
            code.append('                case ' + q(values['VI']) + ': translated = Get(locale, ' + q(key) + '); return;')
    code += ['            }',
             '            // Only exact current catalog names on this known loader-status channel are substituted.',
             '            for (int i = 0; i < CampaignCatalog.RouteCount; i++)', '            {',
             '                string route = CampaignCatalog.GetRoute(i).DisplayName;',
             '                if (raw == "\\u0110ang t\\u1ea3i " + route + "\\u2026")',
             '                { translated = Format(locale, "content.route.loading", new UiTextArgument("route", route)); return; }',
             '            }', '        }', '    }', '}']
    generated = ('\n'.join(code) + '\n').encode('utf-8')
    (HERE / 'UiText.ClientMessages.Generated.cs').write_bytes(generated)
    for language in ORDER:
        data = {'schema': 1, 'locale': language,
                'sourceSha256': hashlib.sha256((HERE / 'canonical-source.json').read_bytes()).hexdigest(),
                'strings': {key: values[language] for key, values in rows.items()}}
        (HERE / (language + '.json')).write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    inventory = json.loads((HERE / 'canonical-source.json').read_text(encoding='utf-8'))
    bindings = []
    for row in inventory['occurrences']:
        value = 'Đang tải {route}…' if row['value'] == 'Đang tải ' else row['value']
        keys = [key for key, values in rows.items() if values['VI'] == value]
        if len(keys) != 1:
            raise ValueError('Source message is unbound: ' + row['file'] + ':' + str(row['line']))
        bindings.append({**row, 'key': keys[0], 'wholeTemplate': value})
    if len(bindings) != 35:
        raise ValueError('Expected 35 reviewed source occurrences')
    report = {'schema': 1, 'keys': len(rows), 'occurrences': bindings,
              'authorSha256': hashlib.sha256((HERE / 'author-client.tsv').read_bytes()).hexdigest(),
              'generatedSha256': hashlib.sha256(generated).hexdigest(),
              'scope': 'Exact known client-owned status/error copy at presentation boundary. Raw session errors, parsing, protocol and state remain unchanged. Unknown text and catalog names are opaque.'}
    (HERE / 'source-bindings.json').write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'keys': len(rows), 'occurrences': len(bindings), 'generatedSha256': report['generatedSha256']}))


if __name__ == '__main__':
    main()
