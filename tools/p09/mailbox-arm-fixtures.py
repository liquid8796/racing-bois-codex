"""Package the published ARM mailbox regression and exact source hashes used by its receipt."""
import hashlib,json,pathlib,tarfile
root=pathlib.Path(__file__).resolve().parents[2]
source_paths=['src/Server/RacingBois.Server.Host/Multiplayer/PeerMailbox.cs','tools/p10/MailboxRaceRepro/Program.cs','tools/p10/MailboxRaceRepro/MailboxRaceRepro.csproj']
expected='1e231c52e99febd2f06354ae6d9a807de41db3d9510ebe86b3498e70a2b1a16e'
if hashlib.sha256((root/source_paths[0]).read_bytes()).hexdigest()!=expected:raise RuntimeError('Unexpected mailbox revision')
out=root/'_local/p09/mailbox-arm-d.tar.gz'
with tarfile.open(out,'w:gz') as archive:
    archive.add(root/'Build/OciStaging/Mailbox-d',arcname='bin')
    for source in source_paths:archive.add(root/source,arcname=source)
receipt={'runtime':'linux-arm64','sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size,
 'sources':[{'path':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in source_paths]}
report=root/'docs/p09/releases/d/mailbox-package.json';report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
