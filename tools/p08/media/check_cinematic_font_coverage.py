"""Read-only source-font cmap coverage; never edits or populates a Unity SDF atlas."""
from pathlib import Path
import argparse
import hashlib
import json
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[3]


def binding(path):
    return {'path': path.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    if args.receipt.exists():
        raise ValueError('Choose a fresh receipt path')
    sources = []
    characters = set()
    for locale in ('ENU', 'DEU', 'ESP', 'FRA', 'ITA', 'VI'):
        path = ROOT / 'tools/p08/media/localization-staging/locales' / (locale + '.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        if data['locale'] != locale or len(data['strings']) != 531:
            raise ValueError('Unexpected cinematic locale inventory')
        for value in data['strings'].values():
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Empty or invalid display copy')
            # Role metadata uses uppercase. Include both cases conservatively.
            characters.update(ord(c) for c in value + value.upper() if not c.isspace())
        sources.append(binding(path))
    fonts = []
    for name in ('NotoSans-Regular.ttf', 'NotoSans-ExtraBold.ttf'):
        path = ROOT / 'Assets/RacingBois/UI/Fonts' / name
        with TTFont(path, lazy=True) as font:
            mapping = font.getBestCmap()
            missing = [code for code in sorted(characters) if not mapping.get(code) or mapping[code] == '.notdef']
            fonts.append({**binding(path), 'missingCodepoints': ['U+' + format(code, '04X') for code in missing]})
    result = {'schema': 1, 'sourceCmapCoveragePassed': all(not row['missingCodepoints'] for row in fonts),
              'distinctNonWhitespaceCodepoints': len(characters), 'locales': sources, 'fonts': fonts,
              'sdfAtlasesModified': False, 'nativeReadabilityAccepted': False,
              'scope': 'Source TrueType Unicode cmap coverage only. This does not verify Unity atlas population, shaping, fallback, wrapping, visual fidelity or readability.'}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2); output.write('\n')
    print(json.dumps(result))
    return 0 if result['sourceCmapCoveragePassed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
