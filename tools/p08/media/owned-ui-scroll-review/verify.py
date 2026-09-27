"""Independent read-only PNG/scroll-evidence verification for the completed native run."""
import hashlib
import json
from pathlib import Path
import struct
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]
RUN='20260928-ui-scroll-01'
PATH=ROOT/f'docs/p08/ui-owned-render/{RUN}-driver.json'
OUT=ROOT/f'docs/p08/ui-owned-render/{RUN}-review.json'
LOCALES={'ENU','DEU','ESP','FRA','ITA','VI'}
SCENARIOS={'career-account-top','career-account-bottom','multiplayer-browser-top','multiplayer-browser-bottom'}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def f32(value): return struct.unpack('<f',struct.pack('<f',value))[0]
def contained(row):
    target,viewport=row['targetBounds'],row['viewportBounds']
    return (target['width']>0 and target['height']>0 and
            f32(target['x'])>=f32(viewport['x']) and f32(target['y'])>=f32(viewport['y']) and
            f32(f32(target['x'])+f32(target['width']))<=f32(f32(viewport['x'])+f32(viewport['width'])) and
            f32(f32(target['y'])+f32(target['height']))<=f32(f32(viewport['y'])+f32(viewport['height'])))

def main():
    if OUT.exists(): raise ValueError('Fresh independent review output required')
    report=json.loads(PATH.read_text(encoding='utf-8-sig'))
    assert report['passed'] is True and report['finished'] is True and not report.get('failure')
    assert report['globalStateUnchanged'] is True and report['ownedRenderObjectsReleased'] is True
    assert len(report['captures'])==48 and report['captureCount']==48 and len(report['scrollPairs'])==24
    assert all(row['passed'] is True for row in report['checks'])
    for name in ['attested-inputs-stable-through-attached-run','global-quality-display-preferences-preserved',
                 'scroll-and-focus-emit-no-gameplay-or-account-command']:
        assert sum(row['name']==name and row['passed'] is True for row in report['checks'])==1
    assert sum(row['name']=='actual-focus-owned-by-visible-target' for row in report['checks'])==48
    captures={}
    companion_count=0
    for row in report['captures']:
        identity=(row['width'],row['locale'],row['scenario'])
        assert identity not in captures and row['locale'] in LOCALES and row['scenario'] in SCENARIOS
        assert row['width'] in {1920,1366} and row['height']==(1080 if row['width']==1920 else 768)
        expected=ROOT/f'docs/p08/ui-owned-render/{RUN}-{row["width"]}/{row["scenario"]}-{row["locale"].lower()}.png'
        assert Path(row['image']).resolve()==expected.resolve() and sha(expected)==row['sha256']
        with Image.open(expected) as image:
            assert image.format=='PNG' and image.size==(row['width'],row['height'])
            image.verify()
        with Image.open(expected) as image:
            image.load()
            extrema=image.getextrema()
            assert any(high>low for low,high in extrema[:3]), 'Clear/flat image cannot establish UI rendering'
        paired=json.loads(expected.with_suffix('.json').read_text(encoding='utf-8-sig'))
        assert paired['sha256']==row['sha256'] and paired['width']==row['width'] and paired['height']==row['height']
        viewport=row['viewport']
        assert viewport['fullyWithinViewport'] is True and contained(viewport)
        assert abs(viewport['offsetY']-(viewport['high'] if row['bottom'] else viewport['low']))<=.01
        if row['scenario'].endswith('-top'):
            assert row['focusedTextField']==('career-username' if row['scenario'].startswith('career') else 'mp-room-name')
        else: assert row['focusedType']=='Button'
        if row.get('companionViewport') is not None:
            assert row['companionViewport']['targetName']=='mp-copy-invite-heading' and contained(row['companionViewport'])
            companion_count+=1
        responsive=row['responsive']
        assert responsive['targetWidth']==row['width'] and responsive['targetHeight']==row['height']
        assert responsive['actualCompact']==(row['width']==1366) and responsive['actualNarrow'] is False
        captures[identity]=row
    assert companion_count==12
    pairs=set()
    ranges=[]
    for row in report['scrollPairs']:
        identity=(row['width'],row['locale'],row['area'])
        assert identity not in pairs and row['area'] in {'career-account','multiplayer-browser'}
        top=captures[(row['width'],row['locale'],row['area']+'-top')]
        bottom=captures[(row['width'],row['locale'],row['area']+'-bottom')]
        assert row['topSha256']==top['sha256'] and row['bottomSha256']==bottom['sha256']
        assert row['topImage']==top['image'] and row['bottomImage']==bottom['image']
        assert row['scrollAvailable'] is True and row['differentOffsets'] is True and row['differentImages'] is True
        assert row['bottomOffset']>row['topOffset'] and top['sha256']!=bottom['sha256']
        assert row['topOffset']==top['viewport']['offsetY'] and row['bottomOffset']==bottom['viewport']['offsetY']
        ranges.append(row['bottomOffset']-row['topOffset']);pairs.add(identity)
    validation=json.loads((ROOT/'tools/p08/media/owned-ui-scroll-staging/validation.json').read_text(encoding='utf-8'))
    changed=[path for path,value in validation['inputHashesBefore'].items() if not Path(path).is_file() or sha(Path(path))!=value]
    assert not changed, 'Frozen preflight inputs changed before this review'
    result=dict(schema=1,passed=True,scope='Independent file/decode/hash/viewport/pair verification of the completed bounded native UI scroll run; not a new native execution.',
                receipt=dict(path=PATH.relative_to(ROOT).as_posix(),sha256=sha(PATH)),pngDecodeAndHashCount=48,
                containedFocusCaptures=48,containedInviteHeadingCaptures=12,distinctScrollablePairs=24,
                minimumTopBottomOffsetDifference=min(ranges),maximumTopBottomOffsetDifference=max(ranges),
                finalNativeSourceBindingPassed=True,independentPreflightInputsUnchanged=True,
                globalStateUnchanged=True,ownedTransientObjectsReleased=True,physicalInputDevicesAccepted=False,
                fullGameAccepted=False,visualConceptAccepted=False,releaseAccepted=False,
                images=[dict(path=Path(row['image']).relative_to(ROOT).as_posix(),sha256=row['sha256']) for row in report['captures']])
    OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ['passed','pngDecodeAndHashCount','containedFocusCaptures','containedInviteHeadingCaptures','distinctScrollablePairs']}))

if __name__=='__main__': main()
