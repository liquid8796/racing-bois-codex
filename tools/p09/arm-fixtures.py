"""Package the exact source files hashed by the native gameplay receipt, with no game assets."""
import hashlib,json,pathlib,sys,tarfile
root=pathlib.Path(__file__).resolve().parents[2]
release=sys.argv[1]
manifest=json.loads((root/'Build/OciStaging'/release/'release.json').read_text())
indexed={item['path']:item['sha256'] for item in manifest['testSource']['files']}
paths=list((root/'Packages/com.racingbois.foundation/Runtime/Definitions').glob('*.cs'))+list((root/'Packages/com.racingbois.foundation/Runtime/Simulation').glob('*.cs'))+[root/'src/Tests/RacingBois.Gameplay.Tests/Program.cs']
out=root/'_local/p09/arm-fixtures.tar.gz'
with tarfile.open(out,'w:gz') as archive:
    for path in paths:
        relative=path.relative_to(root).as_posix()
        if hashlib.sha256(path.read_bytes()).hexdigest()!=indexed[relative]:raise RuntimeError('Native source fixture drift')
        archive.add(path,arcname=relative)
print(out)
