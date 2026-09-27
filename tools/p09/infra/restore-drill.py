#!/usr/bin/env python3
"""Restore an authenticated backup to a new isolated directory; never overwrite live data."""
import hashlib, json, os, pathlib, subprocess, sys, tarfile, tempfile, uuid
from backup import STATE, BACKUPS, KEY, inspect_database, sha

os.umask(0o077)
name=sys.argv[1] if len(sys.argv)==2 else json.loads((BACKUPS/'latest.json').read_text())['archive']
source=(BACKUPS/name).resolve()
if source.parent!=BACKUPS.resolve() or not source.name.startswith('racing-bois-') or source.suffix!='.gpg': raise ValueError('Invalid backup path')
folder=STATE/'restore-drills'/uuid.uuid4().hex; folder.mkdir(parents=True,mode=0o700)
with tempfile.TemporaryDirectory(prefix='decrypt-',dir=STATE) as temp:
    archive=pathlib.Path(temp)/'backup.tar'
    subprocess.run(['gpg','--batch','--yes','--no-symkey-cache','--pinentry-mode','loopback','--passphrase-file',str(KEY),
                    '--output',str(archive),'--decrypt',str(source)],check=True,capture_output=True)
    with tarfile.open(archive) as tar:
        members=tar.getmembers()
        if len(members)!=2 or {m.name for m in members}!={'realm.sqlite3','manifest.json'} or any(not m.isfile() for m in members):
            raise RuntimeError('Unexpected archive members')
        manifest=json.load(tar.extractfile('manifest.json'))
        data=tar.extractfile('realm.sqlite3').read()
        if hashlib.sha256(data).hexdigest()!=manifest['databaseSha256']: raise RuntimeError('Backup hash mismatch')
        (folder/'realm.sqlite3').write_bytes(data)
summary=inspect_database(folder/'realm.sqlite3')
if any(summary[k]!=manifest[k] for k in summary): raise RuntimeError('Restored identity or data changed')
receipt={'status':'passed','scope':'GPG integrity, SQLite integrity/FKs, exact realm, state, balance, ledger and receipt comparison; server startup is tested separately.',
         'archive':source.name,'archiveSha256':sha(source),'restoredDirectory':str(folder),**summary}
(folder/'restore-receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
