"""Verify native UI capture bytes and retained font-preservation receipts."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
LOCALES = ('ENU', 'DEU', 'ESP', 'FRA', 'ITA', 'VI')
SCENARIOS = ('menu', 'settings', 'career-garage', 'career-account',
             'multiplayer-browser', 'multiplayer-room', 'multiplayer-results')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify(receipt_path):
    receipt = read(receipt_path)
    assert receipt['passed'] is True and receipt['finished'] is True
    assert receipt['globalStateUnchanged'] is True
    assert receipt['ownedRenderObjectsReleased'] is True
    assert receipt['physicalInputDeviceAcceptance'] is False
    assert receipt['fullGameAccepted'] is False and receipt['visualConceptAccepted'] is False
    assert all(row['passed'] is True for row in receipt['checks'])
    expected = {(width, height, locale, scenario)
                for width, height in ((1920, 1080), (1366, 768))
                for locale in LOCALES for scenario in SCENARIOS}
    actual = set()
    folders = set()
    verified = []
    for row in receipt['captures']:
        identity = (row['width'], row['height'], row['locale'], row['scenario'])
        assert identity in expected and identity not in actual
        actual.add(identity)
        image = Path(row['image']).resolve(strict=True)
        image.relative_to((ROOT / 'docs/p08/ui-owned-render').resolve())
        assert image.name == row['scenario'] + '-' + row['locale'].lower() + '.png'
        assert sha(image) == row['sha256']
        details_path = image.with_suffix('.json')
        details = read(details_path)
        assert details['sha256'] == row['sha256']
        assert (details['width'], details['height']) == identity[:2]
        with Image.open(image) as picture:
            assert picture.format == 'PNG' and picture.size == identity[:2]
            picture.verify()
        fixture = details['fixture']
        assert fixture['protectedOriginalsPreserved'] is True
        assert fixture['dependencyClosurePassed'] is True and not fixture['failure']
        assert len(fixture['fonts']) == 2
        assert all(font['ownershipPassed'] and font['corpusAdded'] and not font['missing']
                   for font in fixture['fonts'])
        assert len(details['textLayout']) == row['layoutRows'] > 0
        verified.append(dict(path=image.relative_to(ROOT).as_posix(), sha256=sha(image),
                             layoutReceiptSha256=sha(details_path)))
        folders.add(image.parent)
    assert actual == expected and len(verified) == receipt['captureCount'] == 84
    preservation = []
    for folder in sorted(folders):
        released = read(folder / 'released.json')
        assert released['state'] == 'released-render-objects-copies-retained'
        assert released['protectedOriginalsPreserved'] is True and not released['attached']
        for original, expected_hash in released['originalInputs'].items():
            assert sha(ROOT / original) == expected_hash, original
        preservation.append(dict(path=(folder / 'released.json').relative_to(ROOT).as_posix(),
                                 sha256=sha(folder / 'released.json')))
    return dict(schema=1, passed=True, nativeReceiptSha256=sha(receipt_path),
                verifiedPngs=verified, preservationReceipts=preservation,
                nativeChecks=len(receipt['checks']), currentOriginalFilesPreserved=True,
                visualLayoutAccepted=False, physicalInputAccepted=False,
                scope='PNG bytes/dimensions/decoding, native receipt identities and current original-file hashes; no visual-fit or release acceptance.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('output', type=Path)
    arguments = parser.parse_args()
    result = verify(arguments.receipt.resolve(strict=True))
    result['verifierSha256'] = sha(Path(__file__))
    with arguments.output.open('x', encoding='utf-8') as destination:
        json.dump(result, destination, indent=2)
        destination.write('\n')
    print(json.dumps(dict(passed=True, captures=len(result['verifiedPngs']),
                          nativeChecks=result['nativeChecks'], visualLayoutAccepted=False)))
