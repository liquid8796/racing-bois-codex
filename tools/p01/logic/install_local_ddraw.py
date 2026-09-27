"""Extract only pinned upstream DLL into the ignored research runtime copy."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile
from native_project import OUT

root=Path(__file__).resolve().parent
url='https://github.com/FunkyFr3sh/cnc-ddraw/releases/download/v7.1.0.0/cnc-ddraw.zip'
archive=root/'vendor/cnc-ddraw-v7.1.0.0.zip'
archive.parent.mkdir(exist_ok=True)
if not archive.exists():urllib.request.urlretrieve(url,archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='0b13ab89a64c9918189b1dadd449ef6ed3cb3b7b19cabd96d8adbd95505bb908','Unexpected upstream archive hash'
with zipfile.ZipFile(archive) as z:dll=z.read('ddraw.dll')
assert hashlib.sha256(dll).hexdigest()=='85e0f7d530dfda134793a57cb3e76b0287dcc96892ee57162dd68f47283b03a9','Unexpected DLL hash'
target=root/'runtime-copy'
assert target.resolve().parent==root.resolve()
target.mkdir(exist_ok=True)
(target/'ddraw.dll').write_bytes(dll)
(target/'ddraw.ini').write_text('[ddraw]\nwindowed=true\nfullscreen=false\nwidth=640\nheight=480\nrenderer=gdi\ndevmode=true\nnonexclusive=true\nnoactivateapp=true\nmaxfps=60\nmaxgameticks=-1\nsinglecpu=false\nsavesettings=0\nresizable=false\ncenter_window=0\nfixchilds=3\nkeytogglefullscreen=0\nkeytogglefullscreen2=0\nkeytogglemaximize=0\nkeyscreenshot=0\n')
provenance={'project':'FunkyFr3sh/cnc-ddraw','release':'v7.1.0.0','url':url,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'dll_sha256':hashlib.sha256(dll).hexdigest(),'installed_only':str(target/'ddraw.dll'),'config_sha256':hashlib.sha256((target/'ddraw.ini').read_bytes()).hexdigest(),'system_registration':False,'installer_executed':False,'official_support_reference':'https://github.com/FunkyFr3sh/cnc-ddraw','rationale':'Upstream explicitly lists Road Rash and actual windowed mode; GDI software presentation fits original DirectDraw renderer.'}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'ddraw-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(provenance,indent=2))
