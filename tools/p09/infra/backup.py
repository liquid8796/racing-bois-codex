#!/usr/bin/env python3
"""SQLite online backup API -> integrity validation -> encrypted, private, atomic archive."""
import datetime, hashlib, io, json, os, pathlib, sqlite3, subprocess, tarfile, tempfile
from contextlib import closing

STATE=pathlib.Path('/var/lib/racing-bois-staging')
BACKUPS=pathlib.Path('/srv/racing-bois/backups')
KEY=STATE/'backup-key'

def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def inspect_database(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('Backup database integrity failure')
        realm=db.execute('SELECT realm_id,kind,revision,state_json FROM realm WHERE singleton=1').fetchone()
        if not realm or realm[1]!='online': raise RuntimeError('Wrong realm type')
        return {'realmId':realm[0],'realmKind':realm[1],'revision':realm[2],'stateSha256':hashlib.sha256(realm[3].encode()).hexdigest(),
                'profileCount':db.execute('SELECT count(*) FROM profiles').fetchone()[0],
                'creditsTotal':db.execute('SELECT coalesce(sum(credits),0) FROM profiles').fetchone()[0],
                'ledgerCount':db.execute('SELECT count(*) FROM ledger').fetchone()[0],
                'receiptCount':db.execute('SELECT count(*) FROM receipts').fetchone()[0]}

def main():
    os.umask(0o077)
    if not KEY.is_file() or KEY.stat().st_mode & 0o077: raise RuntimeError('Private backup key is missing or insecure')
    BACKUPS.mkdir(mode=0o700,parents=True,exist_ok=True)
    now=datetime.datetime.now(datetime.timezone.utc)
    identifier=now.strftime('%Y%m%dT%H%M%S%fZ')
    target=BACKUPS/f'racing-bois-{identifier}.tar.gpg'
    # Keep staging and final files on the same filesystem (also under systemd bind mounts).
    with tempfile.TemporaryDirectory(prefix='backup-',dir=BACKUPS) as temp:
        tmp=pathlib.Path(temp); copy=tmp/'realm.sqlite3'
        with closing(sqlite3.connect((STATE/'realm'/'realm.sqlite3').as_uri()+'?mode=ro',uri=True)) as source, closing(sqlite3.connect(copy)) as dest:
            source.backup(dest,pages=256,sleep=0.01)
        summary=inspect_database(copy)
        manifest={'schemaVersion':1,'createdUtc':now.isoformat(),'databaseSha256':sha(copy),**summary}
        archive=tmp/'backup.tar'
        with tarfile.open(archive,'w') as tar:
            tar.add(copy,arcname='realm.sqlite3')
            payload=json.dumps(manifest,sort_keys=True).encode()
            item=tarfile.TarInfo('manifest.json'); item.size=len(payload); item.mode=0o600
            tar.addfile(item,io.BytesIO(payload))
        pending=tmp/'encrypted.gpg'
        subprocess.run(['gpg','--batch','--yes','--no-symkey-cache','--pinentry-mode','loopback','--passphrase-file',str(KEY),
                        '--symmetric','--cipher-algo','AES256','--compress-algo','none','--output',str(pending),str(archive)],check=True,capture_output=True)
        with pending.open('rb') as stream: os.fsync(stream.fileno())
        os.replace(pending,target)
        directory_fd=os.open(BACKUPS,os.O_RDONLY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    receipt={'status':'passed','createdUtc':now.isoformat(),'archive':target.name,'archiveSha256':sha(target),'archiveBytes':target.stat().st_size,**summary}
    last=BACKUPS/'latest.json'; last.write_text(json.dumps(receipt,indent=2)); os.chmod(last,0o600)
    print(json.dumps(receipt))

if __name__=='__main__':main()
