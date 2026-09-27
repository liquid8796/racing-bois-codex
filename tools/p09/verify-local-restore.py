"""Verify an off-VM decrypted archive in a temporary private directory, then remove the plaintext copy."""
import hashlib,json,pathlib,sqlite3,subprocess,sys,tarfile,tempfile
from contextlib import closing
root=pathlib.Path(__file__).resolve().parents[2]; private=(root/'_local/p09-recovery').resolve(); archive=pathlib.Path(sys.argv[1]).resolve()
if not archive.is_relative_to(private):raise ValueError('Plaintext verification must remain inside the private recovery directory')
with tempfile.TemporaryDirectory(prefix='restore-',dir=private) as tmp:
    directory=pathlib.Path(tmp).resolve()
    if directory.parent!=private:raise ValueError('Unexpected restore directory')
    # Python's Windows mode-0700 temporary ACL may add Administrators explicitly.
    # Inherit the already restricted recovery-directory ACL before writing private data.
    subprocess.run(['icacls',str(directory),'/reset','/T'],capture_output=True,check=True,creationflags=0x08000000)
    with tarfile.open(archive) as tar:
        if {m.name for m in tar.getmembers()}!={'realm.sqlite3','manifest.json'} or any(not m.isfile() for m in tar.getmembers()):raise ValueError('Unexpected archive content')
        manifest=json.load(tar.extractfile('manifest.json'));data=tar.extractfile('realm.sqlite3').read()
    if hashlib.sha256(data).hexdigest()!=manifest['databaseSha256']:raise RuntimeError('Database hash mismatch')
    database=directory/'realm.sqlite3';database.write_bytes(data)
    with closing(sqlite3.connect(database)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():raise RuntimeError('SQLite integrity failure')
        realm=db.execute('SELECT realm_id,kind,revision,state_json FROM realm').fetchone()
        if realm[:3]!=(manifest['realmId'],manifest['realmKind'],manifest['revision']) or hashlib.sha256(realm[3].encode()).hexdigest()!=manifest['stateSha256']:raise RuntimeError('Realm state changed')
    result=subprocess.run(['dotnet','run','--project',str(root/'tools/p09/RestoreValidation'),'--',str(directory)],cwd=root,capture_output=True,text=True,creationflags=0x08000000)
    if result.returncode or 'RESTORE_PROJECTION_VALIDATED' not in result.stdout:raise RuntimeError('Production storage adapter rejected restored database')
    proof={'status':'passed','databaseSha256':manifest['databaseSha256'],'stateSha256':manifest['stateSha256'],'sqliteIntegrity':True,'foreignKeys':True,'productionWindowsStorageAdapter':True,'plaintextTemporaryCopyRemoved':True}
archive.unlink()
report=root/'docs/p09/off-vm-local-restore.json';report.write_text(json.dumps(proof,indent=2));print(json.dumps(proof))
