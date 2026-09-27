import json,pathlib,hashlib,struct,sys,py_compile
ROOT=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod')
HERE=pathlib.Path(__file__).resolve().parent
OUT=pathlib.Path(r'D:\Project\Unity\racing-bois\docs\reverse-engineering\logic')
def checksum(b):
 total=weighted=alternating=0
 for remaining,value in zip(range(len(b),0,-1),b):
  total+=value;weighted+=remaining*value;alternating+=value if remaining&1 else -value
 return (((alternating<<16)|(total&0xffff))^weighted)&0xffffffff
raw=(ROOT/'RacingBois.exe').read_bytes();sha=hashlib.sha256(raw).hexdigest()
assert sha=='66ab853c5b7b73b82a7c22a0478f5ba5b1066ed27028ef96449f5fe36a6101c5'
index=json.loads((OUT/'function_index.json').read_text(encoding='utf8'))
for item in index:
 off=int(item['file_offset_start'],16);data=raw[off:off+item['length']]
 assert hashlib.sha256(data).hexdigest()==item['sha256_code_slice'],item
saves=sorted((ROOT/'SAVES').glob('*.RRS'))
for save in saves:
 b=save.read_bytes();assert len(b)==160
 assert struct.unpack_from('<I',b,4)[0]==0xcafedead
 assert checksum(b[4:])==struct.unpack_from('<I',b)[0],save
 assert 0<=b[10]<=4 and 0<=b[12]<=14
texts=json.loads((OUT/'localization_strings.json').read_text(encoding='utf8'))
assert len(texts)==6832 and sum(x['file']=='ENU.DLL' for x in texts)==1364
for script in HERE.glob('*.py'):py_compile.compile(str(script),doraise=True)
report={'status':'PASS','source_sha256':sha,'source_game_executed':False,'function_slices_verified':len(index),'saves_validated':len(saves),'localization_strings':len(texts),'english_strings':sum(x['file']=='ENU.DLL' for x in texts),'scripts_syntax_checked':len(list(HERE.glob('*.py'))),'limits':'Static evidence and parser validation only; no dynamic gameplay parity claim.'}
(OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
