"""Freeze display strings only; never rewrite cinematic direction or live Assets."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STORY = ROOT / 'docs/p08/media/cinematic-storyboards.json'

UI = {
    'ui.eyebrow': 'RACING BOIS / STORIES',
    'ui.heading': 'STORIES.',
    'ui.close': 'BACK / ESC',
    'ui.summary': '{0} 3D scenes · Skip at any time',
    'ui.all': 'All',
    'ui.genre': 'CATEGORY',
    'ui.play': 'PLAY SCENE  >',
    'ui.skip': 'SKIP / ESC',
    'ui.shots': '{0} SHOTS',
    'ui.waiting': 'Waiting for the route’s 3D content…',
    'ui.loading': 'Loading the route’s 3D content…',
    'ui.unavailable': 'Scene content is not ready. Load a route first.',
    'ui.failed': 'Could not open this scene. Please try again.',
    'role.Showcase': 'Explore the bikes',
    'role.Busted': 'At the roadside',
    'role.Start': 'On the starting line',
    'role.Win': 'Victory',
    'role.Lose': 'After the race',
    'role.Wreck': 'Back on two wheels',
    'role.Level': 'The next stretch',
    'role.Intro': 'Introduction',
    'role.Duel': 'Two rivals',
    'role.Rival': 'Juno’s story',
    'role.FinalWin': 'The road stays open',
}

def source():
    payload = json.loads(STORY.read_text(encoding='utf-8'))
    strings = dict(UI)
    for scene in payload['definitions']:
        prefix = scene['id'] + '/'
        strings[prefix + 'title'] = scene['title']
        strings[prefix + 'synopsis'] = scene['synopsis']
        for index, beat in enumerate(scene['beats']):
            if beat['index'] != index:
                raise ValueError('Noncontiguous authored beat IDs')
            strings[prefix + 'beat/' + str(index)] = beat['dialogue']
    canonical = json.dumps(strings, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return {'schema': 1, 'locale': 'ENU', 'sourceSha256': hashlib.sha256(canonical).hexdigest(),
            'storyboardsSha256': hashlib.sha256(STORY.read_bytes()).hexdigest(), 'strings': strings}

def main():
    payload = source()
    (HERE / 'locales').mkdir(exist_ok=True)
    (HERE / 'locales/ENU.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    unique = {}
    for key, value in payload['strings'].items():
        unique.setdefault(value, []).append(key)
    rows = [{'index': index, 'english': value, 'keys': keys} for index, (value, keys) in enumerate(unique.items())]
    (HERE / 'source-inventory.json').write_text(json.dumps({'schema': 1, 'sourceSha256': payload['sourceSha256'], 'rows': rows}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / 'source-lines.tsv').write_text(''.join(str(row['index']) + '\t' + row['english'] + '\n' for row in rows), encoding='utf-8')
    print(json.dumps({'keys': len(payload['strings']), 'uniqueSourceStrings': len(rows), 'sourceSha256': payload['sourceSha256']}))

if __name__ == '__main__':
    main()
