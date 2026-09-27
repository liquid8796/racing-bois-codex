"""Windows DPAPI -> GPG stdin. Plaintext key never appears in arguments, environment, files or logs."""
import ctypes,json,pathlib,subprocess,sys,uuid
from ctypes import wintypes
root=pathlib.Path(__file__).resolve().parents[2];private=root/'_local/p09-recovery'
class Blob(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_byte))]
def blob(value):
    buffer=ctypes.create_string_buffer(value)
    return Blob(len(value),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_byte))),buffer
wrapped,keep=blob((private/'backup-key.dpapi').read_bytes());entropy,keep_entropy=blob(b'RacingBois:P09:BackupRecovery:v1');out=Blob()
unprotect=ctypes.windll.crypt32.CryptUnprotectData
unprotect.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
if not unprotect(ctypes.byref(wrapped),None,ctypes.byref(entropy),None,None,0,ctypes.byref(out)):raise RuntimeError('DPAPI recovery failed')
try:key=bytearray(ctypes.string_at(out.data,out.size))
finally:
    ctypes.memset(out.data,0,out.size);ctypes.windll.kernel32.LocalFree(out.data)
receipt=json.loads((root/'docs/p09/off-vm-backup.json').read_text(encoding='utf-8-sig'));archive=private/receipt['archive']
plain=private/('verify-'+uuid.uuid4().hex+'.tar');home=private/'gpg';home.mkdir(exist_ok=True)
def msys_path(path):
    value=path.resolve().as_posix()
    return '/'+value[0].lower()+value[2:]
try:
    result=subprocess.run([r'C:\Program Files\Git\usr\bin\gpg.exe','--batch','--no-symkey-cache','--pinentry-mode','loopback',
                           '--passphrase-fd','0','--homedir',msys_path(home),'--output',msys_path(plain),'--decrypt',msys_path(archive)],input=key+b'\n',capture_output=True,creationflags=0x08000000)
finally:
    for i in range(len(key)):key[i]=0
if result.returncode:raise RuntimeError('GPG authenticated decryption failed with exit '+str(result.returncode))
subprocess.run([sys.executable,str(root/'tools/p09/verify-local-restore.py'),str(plain)],check=True)
