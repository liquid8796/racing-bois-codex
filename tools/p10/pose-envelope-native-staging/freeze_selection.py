"""Bind root-selected imported prefabs; fail if AshV6 is not yet available."""
from pathlib import Path
import argparse
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):value.update(data)
    return value.hexdigest()
def row(name):
    path=ROOT/name
    if not path.is_file():raise FileNotFoundError('Required selected input missing: '+name)
    return {'path':name,'sha256':sha(path),'bytes':path.stat().st_size}
def refs(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):yield value
        for item in value.values():yield from refs(item)
    elif isinstance(value,list):
        for item in value:yield from refs(item)
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='docs/p10/pose-envelope-native-staging/selection.json');args=parser.parse_args()
    target=(ROOT/args.output).resolve()
    if not target.is_relative_to(ROOT/'docs/p10/pose-envelope-native-staging'):raise ValueError('Selection receipt must remain in owned docs folder')
    paths=set()
    for descriptor in ['docs/p08/golden/apex/r4/descriptor.json','docs/p08/golden/ash/v6/descriptor.json']:
        paths.add(descriptor)
        for entry in refs(json.loads((ROOT/descriptor).read_text())):
            if sha(ROOT/entry['path'])!=entry['sha256']:raise ValueError('Art descriptor input changed: '+entry['path'])
            paths.add(entry['path'])
    prepared=json.loads((HERE/'prepared-inputs.json').read_text())
    for entry in prepared['namespaceCopies']:
        if sha(ROOT/entry['source'])!=entry['sourceSha256'] or sha(ROOT/entry['path'])!=entry['sha256']:raise ValueError('Namespace copy changed')
        paths.add(entry['source'])
    paths.update(['tools/p10/pose-envelope-native-staging/prepared-inputs.json','tools/p10/pose-envelope-staging/candidate-manifest.json',
                  'Assets/RacingBois/Client/Presentation/RaceStageView.cs','Assets/RacingBois/Client/Presentation/TrackRibbonView.cs',
                  'Assets/RacingBois/Client/Presentation/RiderAnimationView.cs','Assets/RacingBois/Client/Presentation/RiderAnimationSet.cs',
                  'docs/p10/network/20260927T003126Z/probe.json'])
    result={'schema':1,'bike':row('Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Apex_r4.prefab'),
            'rider':row('Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Ash_V6.prefab'),
            'pipeline':row('Assets/RacingBois/Golden/Generated/StudioReviewPipeline.asset'),
            'fixture':row('Assets/RacingBois/Diagnostics/PoseEnvelopePreview/Data/episodes.json'),
            'inputs':[row(path) for path in sorted(paths)],
            'scope':'Explicit selected current actor candidates, not accepted art; generated prefab/clip/descriptor hashes must match before building.'}
    text=json.dumps(result,indent=2)+'\n'
    if target.exists() and target.read_text()!=text:raise ValueError('Existing selection differs; choose a fresh named receipt')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
    print(json.dumps({'selection':target.relative_to(ROOT).as_posix(),'sha256':sha(target),'inputs':len(result['inputs'])}))
if __name__=='__main__':main()
