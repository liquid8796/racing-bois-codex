"""Expand a human-readable, explicitly authored index<TAB>text worksheet into stable keys."""
import argparse
import json
from pathlib import Path
from prepare_source import HERE, source

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('locale', choices=['DEU', 'ESP', 'FRA', 'ITA', 'VI'])
    parser.add_argument('worksheet', type=Path)
    args = parser.parse_args()
    inventory = json.loads((HERE / 'source-inventory.json').read_text(encoding='utf-8'))
    rows = inventory['rows']
    payload = source()
    if inventory['sourceSha256'] != payload['sourceSha256']:
        raise ValueError('Source inventory is stale; do not rebind old translations to changed text')
    for row in rows:
        if any(payload['strings'].get(key) != row['english'] for key in row['keys']):
            raise ValueError('Source inventory text/key mismatch')
    authored = {}
    for line in args.worksheet.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip():
            continue
        index, value = line.split('\t', 1)
        index = int(index)
        if index in authored or not value.strip():
            raise ValueError('Duplicate/empty translation row: ' + str(index))
        authored[index] = value
    if set(authored) != {row['index'] for row in rows}:
        raise ValueError('Translation worksheet must contain every source row exactly once')
    payload['locale'] = args.locale
    payload['strings'] = {key: authored[row['index']] for row in rows for key in row['keys']}
    (HERE / 'locales' / (args.locale + '.json')).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(args.locale + ': ' + str(len(payload['strings'])) + ' keyed translations')

if __name__ == '__main__':
    main()
