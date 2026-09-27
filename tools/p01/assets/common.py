"""Read-only source adapters shared by P01 research commands."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'tools/reverse-engineering/assets'))
from audit_assets import resources, family_tree, dat_frames, riff_chunks
from dcl import decompress

SOURCE = Path(r'C:\Users\Liquid\Downloads\Unity\racing_bois_mod')
OUTPUT = REPO / 'docs/p01/assets'

def u32(data, offset=0):
    return struct.unpack_from('<I', data, offset)[0]

def signed(value):
    return value if value < 0x80000000 else value - 0x100000000

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def families(source=SOURCE):
    data = (source / 'DATA/FAMILIES.RSC').read_bytes()
    for entry in resources(data)['entries']:
        payload = data[entry['offset']:entry['offset'] + entry['size']]
        raw_size, stored_size, crc, flag = struct.unpack_from('<4I', payload)
        assert stored_size + 16 == len(payload)
        cache = OUTPUT / '.cache' / (digest(payload) + '.fam')
        raw = cache.read_bytes() if cache.exists() else decompress(payload[16:], max_output=raw_size)[0] if flag else payload[16:]
        assert len(raw) == raw_size
        import zlib
        if flag:
            assert zlib.crc32(raw) == crc
        if not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(raw)
        yield entry, raw, family_tree(raw)

def evidence_slices(ranges):
    lines = (REPO / 'docs/reverse-engineering/logic/RacingBois.disassembly.tsv').read_text().splitlines()
    index = []
    for name, start, end, description in ranges:
        selected = [line for line in lines if start <= int(line.split('\t')[0], 16) < end]
        target = OUTPUT / 'evidence' / (name + '.tsv')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('\n'.join(selected) + '\n', encoding='utf-8')
        index.append({'name': name, 'start_va': hex(start), 'end_va_exclusive': hex(end),
                      'description': description, 'instructions': len(selected),
                      'path': target.relative_to(OUTPUT).as_posix()})
    save_json(OUTPUT / 'evidence/index.json', index)

def verify_source():
    expected = json.loads((REPO / 'docs/reverse-engineering/assets/source_manifest.json').read_text())
    failures = []
    actual = {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()}
    assert actual == {row['path'] for row in expected}
    for row in expected:
        if digest((SOURCE / row['path']).read_bytes()) != row['sha256']:
            failures.append(row['path'])
    assert not failures, failures
    return {'files': len(expected), 'sha256_unchanged': True}
