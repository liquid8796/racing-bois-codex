"""Publish a fresh source-bound ARM64 staging package without relying on a Git clean state."""
from __future__ import annotations
import argparse, datetime, hashlib, json, pathlib, subprocess, tarfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

def digest(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()

def sources(include_tests=False):
    files = []
    roots = ['src/Server', 'src/Shared'] + ['Packages/com.racingbois.foundation/Runtime/'+name for name in ('Definitions','Simulation','Protocol','NetworkMapping')]
    if include_tests: roots += ['src/Tests','tools/p09/HostPolicyTests']
    for base in roots:
        if not (ROOT/base).is_dir(): raise RuntimeError(f'Required source root is missing: {base}')
        for p in (ROOT / base).rglob('*'):
            if p.is_file() and p.suffix in ('.cs', '.csproj', '.props', '.json') and not {'bin','obj'} & set(p.parts):
                files.append(p)
    files += [ROOT/'src/Directory.Build.props', ROOT/'src/global.json']
    rows = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': digest(p)} for p in sorted(set(files))]
    return {'sha256': hashlib.sha256(json.dumps(rows, separators=(',',':')).encode()).hexdigest(), 'files': rows}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('release'); args = parser.parse_args()
    if not args.release or len(args.release)>48 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.release):
        raise ValueError('Use a short lowercase release ID.')
    out = ROOT/'Build'/'OciStaging'/args.release
    out.mkdir(parents=True, exist_ok=False)
    before = sources(); tests_before = sources(include_tests=True)
    projects = {'server':'src/Server/RacingBois.Server.Host', 'tests/persistence':'src/Tests/RacingBois.Persistence.Tests',
                'tests/multiplayer':'src/Tests/RacingBois.Multiplayer.Integration.Tests', 'tests/gameplay':'src/Tests/RacingBois.Gameplay.Tests'}
    for target, project in projects.items():
        subprocess.run(['dotnet','publish', str(ROOT/project), '-c','Release','-r','linux-arm64','--self-contained','true',
                        '-o',str(out/target), '--nologo','-v','quiet'], cwd=ROOT, check=True)
    after = sources()
    if before != after or tests_before != sources(include_tests=True): raise RuntimeError('Source changed while publishing. Do not deploy this package.')
    manifest = {'schemaVersion':1, 'releaseId':args.release, 'generatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'scope':'Backend-only P09 staging; no P08 content acceptance or desktop release claim.', 'runtime':'linux-arm64',
                'source':before, 'testSource':tests_before, 'files':[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
                                        for p in sorted(out.rglob('*')) if p.is_file()]}
    (out/'release.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive = out.with_suffix('.tar.gz')
    seen = {}
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(out.rglob('*')):
            relative=p.relative_to(out).as_posix()
            if p.is_dir(): tar.add(p,arcname=relative,recursive=False); continue
            content_hash=digest(p)
            if content_hash in seen:
                member=tar.gettarinfo(p,arcname=relative); member.type=tarfile.LNKTYPE; member.linkname=seen[content_hash]; member.size=0
                tar.addfile(member)
            else:
                seen[content_hash]=relative; tar.add(p,arcname=relative,recursive=False)
    receipt = {'releaseId':args.release,'sourceSha256':before['sha256'],'archive':str(archive),'archiveSha256':digest(archive),'archiveBytes':archive.stat().st_size}
    reports=ROOT/'docs'/'p09';reports.mkdir(parents=True,exist_ok=True)
    (reports/f'{args.release}-package.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__': main()
