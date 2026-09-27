"""Verify the 108-image native fit run without treating duplicate scroll views as coverage."""
import argparse
import json
import math
from pathlib import Path

from PIL import Image
from verify_owned_ui_capture import ROOT, LOCALES, read, sha

SCENARIOS = ('menu', 'settings', 'career-garage', 'career-account', 'career-account-bottom',
             'multiplayer-browser', 'multiplayer-browser-actions', 'multiplayer-room', 'multiplayer-results')


def verify(path):
    native = read(path)
    for field in ('passed', 'finished', 'globalStateUnchanged', 'ownedRenderObjectsReleased',
                  'ownedTargetClearedBeforeEachRender'):
        assert native[field] is True, field
    for field in ('actualNetwork', 'physicalInputDeviceAcceptance', 'fullGameAccepted', 'visualConceptAccepted'):
        assert native[field] is False, field
    assert all(item['passed'] is True for item in native['checks'])
    expected = {(w, h, locale, case) for w, h in ((1920, 1080), (1366, 768))
                for locale in LOCALES for case in SCENARIOS}
    captures = {}
    verified = []
    folders = set()
    for row in native['captures']:
        identity = (row['width'], row['height'], row['locale'], row['scenario'])
        assert identity in expected and identity not in captures
        captures[identity] = row
        image = Path(row['image']).resolve(strict=True)
        image.relative_to((ROOT / 'docs/p08/ui-owned-render').resolve())
        assert image.name == row['scenario'] + '-' + row['locale'].lower() + '.png'
        assert sha(image) == row['sha256']
        layout_path = image.with_suffix('.json')
        details = read(layout_path)
        assert details['sha256'] == row['sha256'] and (details['width'], details['height']) == identity[:2]
        with Image.open(image) as picture:
            assert picture.format == 'PNG' and picture.size == identity[:2]
            picture.verify()
        fixture = details['fixture']
        assert fixture['protectedOriginalsPreserved'] and fixture['dependencyClosurePassed'] and not fixture['failure']
        assert len(fixture['fonts']) == 2
        assert all(font['ownershipPassed'] and font['corpusAdded'] and not font['missing'] for font in fixture['fonts'])
        assert len(details['textLayout']) == row['layoutRows'] > 0
        responsive = row['responsive']
        assert (responsive['targetWidth'], responsive['targetHeight']) == identity[:2]
        assert responsive['actualCompact'] == responsive['expectedCompact'] == (row['width'] < 1440 or row['height'] < 900)
        assert responsive['actualNarrow'] == responsive['expectedNarrow']
        verified.append(dict(path=image.relative_to(ROOT).as_posix(), sha256=sha(image), layoutSha256=sha(layout_path)))
        folders.add(image.parent)
    assert set(captures) == expected and len(captures) == native['captureCount'] == 108
    buttons, headings = native['singleLineActionMeasurements'], native['inviteHeadingMeasurements']
    assert buttons and len(headings) == 12
    for row in buttons + headings:
        assert row['validMeasurement'] and row['fitsWidth']
        for key in ('signedDifferenceLogical', 'signedDifferenceOutputPixels', 'roundingBoundOutputPixels'):
            assert math.isfinite(row[key])
        assert 0 <= row['roundingBoundOutputPixels'] <= 0.001
        assert row['signedDifferenceOutputPixels'] <= row['roundingBoundOutputPixels']
    duplicate_pairs = []
    for w, h in ((1920, 1080), (1366, 768)):
        for locale in LOCALES:
            for top, bottom in (('career-account', 'career-account-bottom'),
                                ('multiplayer-browser', 'multiplayer-browser-actions')):
                if captures[(w, h, locale, top)]['sha256'] == captures[(w, h, locale, bottom)]['sha256']:
                    duplicate_pairs.append(dict(width=w, locale=locale, top=top, bottom=bottom))
    for folder in folders:
        released = read(folder / 'released.json')
        assert released['state'] == 'released-render-objects-copies-retained'
        assert released['protectedOriginalsPreserved'] and not released['attached']
        for source, expected_hash in released['originalInputs'].items():
            assert sha(ROOT / source) == expected_hash, source
    return dict(schema=2, passed=True, nativeReceiptSha256=sha(path), pngs=verified,
                nativeChecks=len(native['checks']), buttonMeasurements=len(buttons), headingMeasurements=len(headings),
                responsiveObservations=len(captures), duplicateScrollPairs=duplicate_pairs,
                distinctScrollCoverageAccepted=False, visualConceptAccepted=False, physicalInputAccepted=False,
                scope='Actual PNG/hash/decode, native fit and target-breakpoint receipts, current original UI/font files. Separate explicit-scroll coverage remains required.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = verify(args.receipt.resolve(strict=True))
    result['verifierSha256'] = sha(Path(__file__))
    with args.output.open('x', encoding='utf-8') as destination:
        json.dump(result, destination, indent=2)
        destination.write('\n')
    print(json.dumps({key: value for key, value in result.items()
                      if key in ('passed', 'nativeChecks', 'buttonMeasurements', 'headingMeasurements', 'responsiveObservations', 'duplicateScrollPairs')}))
