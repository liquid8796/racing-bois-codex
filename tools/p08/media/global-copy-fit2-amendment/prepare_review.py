"""Bind run05's actual visual finding and summarize its failed raw metric receipt."""
import collections
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RECEIPT = 'docs/p08/ui-owned-render/20260928-ui-render-05-driver.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    destinations = [HERE / 'changes.json', HERE / 'run05-review.json']
    if any(path.exists() for path in destinations):
        raise SystemExit('Fresh review outputs required')
    source = ROOT / RECEIPT
    report = json.loads(source.read_text(encoding='utf-8-sig'))
    assert report['finished'] and not report['passed'] and report['captureCount'] == 108
    union_path = ROOT / 'tools/p08/media/global-copy-fit-amendment/authored-text-union.json'
    union = json.loads(union_path.read_text(encoding='utf-8'))
    key = 'multiplayer.browser.invite-heading'
    before = 'EINEN CODE VON FREUNDEN ERHALTEN?'
    assert union['texts']['DEU']['global'][key] == before
    evidence = []
    for width in (1920, 1366):
        path = f'docs/p08/ui-owned-render/20260928-ui-render-05-{width}/multiplayer-browser-actions-deu.png'
        evidence.append(dict(path=path, sha256=sha(ROOT / path)))
    changes = [dict(provider='Multiplayer', locale='DEU', key=key, before=before,
                    after='CODE VON FREUNDEN?', protectedTokens=[], evidence=evidence,
                    reason='Actual lower-scroll images at both output sizes clip the invite-code heading at the right edge of the create/join column. Shorten the same invitation question; preserve typography, geometry and behavior. This Label is outside run05 Button-only width measurement.')]
    measurements = report['singleLineActionMeasurements']
    failures = [row for row in measurements if not row['fitsWidth']]
    observations = collections.Counter((row['width'], row['responsive']['screenWidth'], row['responsive']['screenHeight'],
                                       row['responsive']['actualCompact'], row['responsive']['actualNarrow']) for row in report['captures'])
    validation = json.loads((ROOT / 'tools/p08/media/owned-ui-driver-r4-staging/validation.json').read_text(encoding='utf-8'))
    changed_inputs = [path for path, expected in validation['inputHashesBefore'].items()
                      if not Path(path).is_file() or sha(Path(path)) != expected]
    review = dict(
        schema=1, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        nativeReceipt=dict(path=RECEIPT, sha256=sha(source)), nativePassed=False,
        captures=report['captureCount'], measurementCount=len(measurements),
        strictFailureCount=len(failures),
        strictFailuresByWidth=dict(collections.Counter(row['width'] for row in failures)),
        minimumPositiveOverflowLogical=min(row['overflowWidth'] for row in failures),
        maximumPositiveOverflowLogical=max(row['overflowWidth'] for row in failures),
        failuresAboveOneThousandthLogicalUnit=sum(row['overflowWidth'] > .001 for row in failures),
        interpretation='All strict Button failures are tiny single-precision-scale deltas; no visibly clipped Button was confirmed in the targeted image review. This analysis does not rewrite or pass the failed native receipt. A reviewed precision-aware diagnostic is still required.',
        responsiveObservations=[dict(targetWidth=key[0], screenWidth=key[1], screenHeight=key[2], compact=key[3], narrow=key[4], count=count)
                                for key, count in sorted(observations.items())],
        historical1920Controls=[row for row in report['checks'] if row['name'] == 'historical-overflow-negative-control'],
        historical1366Observations=report['historicalCompactObservations'],
        globalStateUnchanged=report['globalStateUnchanged'], ownedRenderObjectsReleased=report['ownedRenderObjectsReleased'],
        nativeEndInputCheckReached=any(row['name'] == 'attested-inputs-stable-through-attached-run' for row in report['checks']),
        independentPostReadOfPreflightInputs=dict(changed=changed_inputs, scope='Independent read of frozen preflight files after run05. This is not a claim that the aborted native end-binding assertion executed.'),
        confirmedNewVisualFindings=1, conceptAccepted=False, releaseAccepted=False,
    )
    for destination, data in zip(destinations, (changes, review)):
        destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(nativePassed=False, captures=review['captures'], strictFailures=len(failures),
                         maximumOverflow=review['maximumPositiveOverflowLogical'], changedInputs=len(changed_inputs), visualFindings=1)))

if __name__ == '__main__':
    main()
