"""Validate research parsers, media decoding, and unchanged source-file hashes."""
from audit_assets import *

def rejected(callback):
    try: callback()
    except (ValueError, AssertionError, IndexError, struct.error): return True
    raise AssertionError('Malformed input was accepted')

def main():
    root=pathlib.Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod')
    out=pathlib.Path('docs/reverse-engineering/assets')
    manifest=json.loads((out/'source_manifest.json').read_text())
    changes=[f['path'] for f in manifest if sha((root/f['path']).read_bytes())!=f['sha256']]
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert not changes and actual=={f['path'] for f in manifest}
    fixture=bytes.fromhex('00 04 82 24 25 8f 80 7f')
    assert decompress(fixture)==(b'AIAIAIAIAIAIA',8)
    for i in range(len(fixture)): rejected(lambda:decompress(fixture[:i]))
    rejected(lambda:decompress(fixture,max_output=12))
    rejected(lambda:decompress(b'\x02\x04'))
    rejected(lambda:decompress(b'\x00\x03'))
    assert len(dat_frames(b'\x00\x00\x02\x02ABCD'))==2
    rejected(lambda:dat_frames(b'\x02\x02ABC'))
    rejected(lambda:dat_frames(b'\x02\x00'))
    for f in manifest:
        if f['magic_type']=='CRSR':
            d=(root/f['path']).read_bytes(); resources(d)
            rejected(lambda:resources(d[:80]))
    files=sorted((root/'VIDEO').rglob('*.AVI'))
    def run(p):
        q=subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(p),'-map','0','-f','null','NUL'],capture_output=True,text=True,timeout=90)
        return {'path':p.relative_to(root).as_posix(),'returncode':q.returncode,'stderr':q.stderr.strip(),'all_streams_fully_decoded':q.returncode==0 and not q.stderr.strip()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: decoded=list(pool.map(run,files))
    dump(out/'video_decode_validation.json',decoded)
    assert all(x['all_streams_fully_decoded'] for x in decoded)
    chunks=json.loads((out/'riff_chunks.json').read_text())
    avi_counts=[{'path':x['path'],'video_00dc_chunks':sum(c['path'].endswith('/00dc') and '/movi/' in c['path'] for c in x['chunks']),'audio_01wb_chunks':sum(c['path'].endswith('/01wb') and '/movi/' in c['path'] for c in x['chunks'])} for x in chunks if x['form']=='AVI ']
    media=json.loads((out/'media_metadata.json').read_text())
    expected={x['path']:sum(int(s.get('nb_frames',0)) for s in x.get('streams',[]) if s.get('codec_type')=='video') for x in media if x['path'].endswith('.AVI')}
    assert all(x['video_00dc_chunks']==expected[x['path']] for x in avi_counts)
    dump(out/'avi_chunk_counts.json',avi_counts)
    result={'source_files_sha256_unchanged':len(manifest),'source_path_set_unchanged':True,'upstream_blast_known_vector':'PASS','truncated_dcl_prefixes_rejected':len(fixture),'output_limit_rejected':True,'malformed_dcl_headers_rejected':True,'dat_empty_and_nonempty_records':'PASS','truncated_dat_rejected':True,'crsr_files_validated':13,'truncated_crsr_rejected':True,'avi_all_streams_fully_decoded':len(decoded),'avi_video_chunks_match_header_frames':sum(x['video_00dc_chunks'] for x in avi_counts),'avi_audio_chunks':sum(x['audio_01wb_chunks'] for x in avi_counts)}
    dump(out/'validation.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__': main()
