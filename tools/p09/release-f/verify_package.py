"""Read-only verification of the immutable local protocol6 ARM package."""
from pathlib import Path
import hashlib,json,struct,tarfile
ROOT=Path(__file__).resolve().parents[3];REPORT=ROOT/'docs/p09/releases/f'
receipt=json.loads((REPORT/'package.json').read_text());folder=ROOT/'Build/OciStaging'/receipt['releaseId'];manifest=json.loads((folder/'release.json').read_text())
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert digest(Path(receipt['archive']))==receipt['archiveSha256']
assert digest(Path(receipt['armFixturesArchive']))==receipt['armFixturesSha256']
assert digest(folder/'release.json')==receipt['manifestSha256']
for row in manifest['files']:
    path=folder/row['path'];assert path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],row['path']
for group in ['source','testSource']:
    for row in manifest[group]['files']:assert digest(ROOT/row['path'])==row['sha256'],row['path']
with tarfile.open(receipt['archive']) as tar:
    names={member.name for member in tar.getmembers() if member.isfile() or member.islnk()}
    assert names=={row['path'] for row in manifest['files']}|{'release.json'}
    for row in manifest['files']:
        with tar.extractfile(row['path']) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256'],row['path']
entries=[]
for relative in ['server/RacingBois.Server.Host','tests/persistence/RacingBois.Persistence.Tests','tests/multiplayer/RacingBois.Multiplayer.Integration.Tests',
                 'tests/gameplay/RacingBois.Gameplay.Tests','tests/prediction/RacingBois.Prediction.Tests','tests/prediction-projection/RacingBois.PredictionProjection.Tests','tests/p05-client/RacingBois.P05Client.Tests']:
    data=(folder/relative).read_bytes()[:64]
    assert data[:4]==b'\x7fELF' and data[4]==2 and data[5]==1 and struct.unpack_from('<H',data,18)[0]==183,relative
    entries.append({'path':relative,'format':'ELF64 little-endian AArch64','sha256':digest(folder/relative)})
result={'schema':1,'status':'PASS','releaseId':receipt['releaseId'],'archiveSha256':receipt['archiveSha256'],'verifiedFiles':len(manifest['files']),
        'sourceSha256':manifest['source']['sha256'],'testSourceSha256':manifest['testSource']['sha256'],'armEntryPoints':entries,
        'scope':'Local immutable archive/source/file hashes and ARM64 format only. No upload, remote execution or activation.'}
(REPORT/'local-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','releaseId','verifiedFiles','sourceSha256']}))
