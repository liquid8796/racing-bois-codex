"""Expand an authored index<TAB>translation worksheet against the frozen semantic source."""
import argparse
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('locale', choices=['DEU', 'ESP', 'FRA', 'ITA'])
parser.add_argument('worksheet', type=Path)
args = parser.parse_args()
source_bytes = (HERE / 'canonical-source.json').read_bytes()
source = json.loads(source_bytes)
freeze = json.loads((HERE / 'templates-freeze.json').read_text())
source_hash = hashlib.sha256(source_bytes).hexdigest()
if source_hash != freeze['canonicalSourceSha256']:
    raise ValueError('Canonical semantic templates changed after freeze')
values = {}
for line in args.worksheet.read_text(encoding='utf-8-sig').splitlines():
    if not line.strip(): continue
    index, value = line.split('\t', 1)
    index = int(index)
    if index in values: raise ValueError('Duplicate worksheet index')
    values[index] = value.replace('\\n', '\n')
if set(values) != set(range(len(source['entries']))):
    raise ValueError('Worksheet must cover every semantic key exactly once')
strings = {}
for index, entry in enumerate(source['entries']):
    value = values[index]
    if not value.strip() or re.findall(r'\{[^}]*\}', value) != re.findall(r'\{[^}]*\}', entry['enu']):
        # Reordering named arguments is valid; multiplicity still must match.
        if not value.strip() or sorted(re.findall(r'\{[^}]*\}', value)) != sorted(re.findall(r'\{[^}]*\}', entry['enu'])):
            raise ValueError('Blank copy or placeholder mismatch: ' + entry['key'])
    if value.count('\n') != entry['vi'].count('\n'):
        raise ValueError('Explicit line breaks changed: ' + entry['key'])
    strings[entry['key']] = value
payload = {'schema':1,'locale':args.locale,'boundary':source['boundary'],'sourceSha256':source_hash,'strings':strings}
(HERE / 'locales' / (args.locale + '.json')).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'locale':args.locale,'keys':len(strings),'nativeAcceptance':False}))
