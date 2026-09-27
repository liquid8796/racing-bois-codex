"""Bind explicitly authored worksheet rows to the frozen semantic multiplayer keys."""
import argparse
import hashlib
import json
from pathlib import Path
from template_rules import validate_template

HERE = Path(__file__).resolve().parent
SEMANTICS_SHA256 = 'b8d23d0277a7db55645d8d26fb64395e3e62d9b3ad83365ee8dcaa1d4fa097e5'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('locale', choices=['ENU', 'DEU', 'ESP', 'FRA', 'ITA'])
    parser.add_argument('rows', type=Path)
    args = parser.parse_args()
    source_path = HERE / 'canonical-source.json'
    raw = source_path.read_bytes()
    source = json.loads(raw)
    semantics = json.dumps([(entry['vi'], entry['arguments']) for entry in source['entries']], ensure_ascii=False, separators=(',', ':')).encode('utf8')
    if hashlib.sha256(semantics).hexdigest() != SEMANTICS_SHA256:
        raise ValueError('Authored row order/text/argument semantics changed; review translations before rebinding.')
    rows = {}
    for line in args.rows.read_text(encoding='utf8').splitlines():
        if not line:
            continue
        number, separator, value = line.partition('\t')
        if not separator or not number.isdecimal() or int(number) in rows:
            raise ValueError('Expected unique index TAB authored translation: ' + line)
        rows[int(number)] = value.replace('\\n', '\n')
    if set(rows) != set(range(len(source['entries']))):
        raise ValueError('Translation index coverage differs from frozen source.')
    translated = {}
    for index, entry in enumerate(source['entries']):
        value = rows[index]
        validate_template(value, entry['vi'])
        translated[entry['key']] = value
    target = HERE / 'locales' / (args.locale + '.json')
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(dict(schema=1, locale=args.locale, sourceSha256=hashlib.sha256(raw).hexdigest(),
                                     entries=translated, nativeUiAccepted=False), ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(locale=args.locale, entries=len(translated), path=str(target))))


if __name__ == '__main__':
    main()
