"""Root-invoked reviewed installation only. Default verifies/prints; --apply writes new diagnostic files, never frozen Client."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import uuid
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;DEST=ROOT/'Assets/RacingBois/Diagnostics/PoseEnvelopePreview'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def files():
    return [p for folder in ['Runtime','Editor','Data'] for p in sorted((HERE/folder).rglob('*')) if p.is_file() and p.suffix in {'.cs','.asmdef','.json'}]
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    prepared=json.loads((HERE/'prepared-inputs.json').read_text())
    for entry in prepared['namespaceCopies']:
        original=(ROOT/entry['source']).read_bytes();transformed=original.replace(entry['from'].encode(),entry['to'].encode())
        if sha(ROOT/entry['source'])!=entry['sourceSha256'] or transformed!=(ROOT/entry['path']).read_bytes() or sha(ROOT/entry['path'])!=entry['sha256']:raise ValueError('Frozen namespace copy does not match')
    if sha(ROOT/prepared['comparisonVariant']['path'])!=prepared['comparisonVariant']['sha256']:raise ValueError('20m comparison fork changed')
    rows=[]
    for source in files():
        relative=source.relative_to(HERE);target=DEST/relative
        for part in [target,*target.parents]:
            if part==ROOT:break
            if part.is_symlink() or getattr(part,'is_junction',lambda:False)():raise ValueError('No reparse-point installation paths')
        if target.exists() and target.read_bytes()!=source.read_bytes():raise ValueError('Refuse different installed diagnostic: '+str(relative))
        rows.append({'source':source.relative_to(ROOT).as_posix(),'path':target.relative_to(ROOT).as_posix(),'sha256':sha(source),'bytes':source.stat().st_size})
    if args.apply:
        temporary_root=ROOT/'_local/p10-pose-preview-install';temporary_root.mkdir(parents=True,exist_ok=True)
        for row in rows:
            source=ROOT/row['source'];target=ROOT/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():continue
            temporary=temporary_root/('copy-'+uuid.uuid4().hex)
            try:
                temporary.write_bytes(source.read_bytes());os.link(temporary,target)
            finally:temporary.unlink(missing_ok=True)
            if sha(target)!=row['sha256']:raise ValueError('Copy hash mismatch')
    result={'schema':1,'installed':args.apply,'unityCalled':False,'productionClientWritten':False,'files':rows}
    if args.apply:
        output=ROOT/'docs/p10/pose-envelope-native-staging/installed.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'installed':args.apply,'files':len(rows),'target':DEST.relative_to(ROOT).as_posix()}))
if __name__=='__main__':main()
