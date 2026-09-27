"""Decode every NOD/SGS resource, retaining fields whose units are unknown.

Does not fabricate a spline from unproven byte meanings. The native loader is
the schema authority: 0x447b80, 0x447db0, 0x447e50 and 0x448030.
"""
from common import *
from collections import Counter
import csv


def decode_nod(data):
    assert data[:4] == b'DONR' and u32(data, 4) == len(data)
    count, flags, root = struct.unpack_from('<3I', data, 8)
    nodes = []
    offset = 20
    for index in range(count):
        kind, node_flags = struct.unpack_from('<2I', data, offset)
        assert kind in range(5), (index, kind)
        size = 32 if kind <= 2 else 8
        assert offset + size <= len(data)
        words = list(struct.unpack_from('<' + 'I' * (size // 4), data, offset))
        links = words[2:4] if kind == 0 else words[2:5] if kind in (1, 2) else []
        nodes.append({'index': index, 'offset': offset, 'bytes': size, 'type': kind,
                      'flags': node_flags, 'links': links, 'raw_u32': words,
                      'segment_index': words[4] if kind == 0 else None,
                      'node_length_raw': words[5] if kind == 0 else None})
        offset += size
    assert offset == len(data)
    by_offset = {n['offset']: n for n in nodes}
    assert root in by_offset
    assert all(link in by_offset for n in nodes for link in n['links'])
    visited, queue = set(), [root]
    while queue:
        here = queue.pop()
        if here in visited:
            continue
        visited.add(here)
        queue.extend(by_offset[here]['links'])
    return {'count': count, 'flags': flags, 'root_offset': root, 'nodes': nodes,
            'all_nodes_reachable': len(visited) == count,
            'unreachable_offsets': sorted(set(by_offset) - visited)}


def decode_sgs(data):
    assert data[:4] == b'SGSR' and u32(data, 4) == len(data)
    count = u32(data, 8)
    assert 16 + count * 52 <= len(data)
    segments, offsets = [], set()
    for index in range(count):
        raw = list(struct.unpack_from('<13I', data, 16 + index * 52))
        # Loader relocates slots 1..12. Zero is a null pointer. Slot 12 is
        # overwritten with the runtime sequential id after relocation.
        assert all(v == 0 or 16 + count * 52 <= v < len(data) for v in raw[1:])
        refs = [{'slot': i, 'byte_offset_in_record': i * 4, 'chunk_offset': v}
                for i, v in enumerate(raw[1:], 1) if v]
        offsets.update(v for v in raw[1:] if v)
        segments.append({'index': index, 'offset': 16 + index * 52,
                         'slot0_runtime_length_overwritten': raw[0], 'raw_u32': raw, 'references': refs})
    chunks = []
    for offset in sorted(offsets):
        tag = data[offset:offset+4][::-1].decode('ascii')
        size, count_field = struct.unpack_from('<2I', data, offset+4)
        assert size >= 12 and offset + size <= len(data)
        raw = data[offset:offset+size]
        # Fixed-layout chunks are proven across corpus. Units remain explicit
        # raw values until connected to the gameplay consumer.
        rec = {'offset': offset, 'tag': tag, 'bytes': size, 'count_field': count_field,
               'sha256': digest(raw), 'raw_hex': raw.hex()}
        schemas = {'RROB': (20, 4), 'RRSM': (24, 12), 'RSLD': (16, 36),
                   'RLAN': (16, 20), 'RHZD': (16, 8), 'RSEC': (20, 12),
                   'RHIL': (20, 76)}
        if tag in ('RPTH', 'RBLD'):
            assert size == (16 + count_field * 2 + 3) & ~3, (tag, size, count_field)
            rec['header_raw_u32'] = list(struct.unpack_from('<4I', raw))
            rec['samples_raw_s8_pairs'] = [list(struct.unpack_from('<bb', raw, 16+i*2)) for i in range(count_field)]
            rec['schema_status'] = '16-byte header; count 2-byte samples; coordinate meaning not yet locked'
            if tag == 'RPTH':
                first,last=struct.unpack_from('<hh',raw,12)
                accumulator=[first]
                for pair in rec['samples_raw_s8_pairs']:
                    accumulator.append(accumulator[-1]+pair[1])
                rec['endpoint_accumulator_start_raw']=first
                rec['endpoint_accumulator_end_raw']=last
                rec['reconstructed_accumulator_raw']=accumulator
                rec['endpoint_sum_matches_header']=accumulator[-1]==last
                rec['schema_status']='signed16 forward/reverse accumulator seeds; signed8 coefficient pairs; 256-unit longitudinal step; world units open'
        elif tag == 'RMTN':
            left_count,right_count=struct.unpack_from('<2I',raw,12)
            samples_offset=24+16*(left_count+right_count)
            assert size == (samples_offset+2*count_field+3)&~3
            rec['header_raw_u32']=list(struct.unpack_from('<6I',raw))
            rec['first_bank_count']=left_count
            rec['second_bank_count']=right_count
            rec['bank_records_raw_hex']=[raw[24+16*i:40+16*i].hex() for i in range(left_count+right_count)]
            rec['samples_raw_s8_pairs']=[list(struct.unpack_from('<bb',raw,samples_offset+2*i)) for i in range(count_field)]
            rec['schema_status']='two16-byte record banks and per-sample2-byte stream; 0x45112d native offsets confirmed; field units open'
        elif tag in schemas:
            header, stride = schemas[tag]
            assert size == header + count_field * stride, (tag, size, count_field, header, stride)
            rec['header_raw_u32'] = list(struct.unpack_from('<'+'I'*(header//4), raw))
            rec['record_bytes'] = stride
            rec['records_raw_hex'] = [raw[header+i*stride:header+(i+1)*stride].hex() for i in range(count_field)]
            rec['schema_status'] = 'record boundaries validated; field semantics partially open'
            if tag=='RRSM':
                rec['stream_events']=[]
                for i in range(count_field):
                    p=24+i*12
                    distance,packed,resource=struct.unpack_from('<3I',raw,p)
                    rec['stream_events'].append({'index':i,'longitudinal_sample_raw':signed(distance),
                                                'operation_state':raw[p+4],'family_slot':raw[p+5],
                                                'flags_raw':list(raw[p+6:p+8]),'resource_word_raw':resource,
                                                'family_id_when_state1':resource&65535 if raw[p+4]==1 else None})
                rec['schema_status']='family stream events: position+0, state+4,slot+5,FAM id+8 low16 for state1; native0x44b170/0x452310'
        else:
            rec['schema_status'] = 'raw chunk retained; variable layout not yet assigned'
        chunks.append(rec)
    ordered = sorted(chunks, key=lambda c: c['offset'])
    assert all(a['offset']+a['bytes'] <= b['offset'] for a,b in zip(ordered, ordered[1:]))
    assert ordered[0]['offset'] == 16 + count * 52
    assert ordered[-1]['offset'] + ordered[-1]['bytes'] == len(data)
    assert all(a['offset']+a['bytes'] == b['offset'] for a,b in zip(ordered, ordered[1:])), 'Unparsed gaps'
    return {'segment_count': count, 'header_slot12_raw': u32(data, 12), 'segments': segments,
            'chunks': chunks, 'all_payload_bytes_accounted': True}


def main():
    summary = []
    for path in sorted((SOURCE / 'DATA/COURSES').glob('*.CRS')):
        data = path.read_bytes()
        entries = {e['type'].strip(): e for e in resources(data)['entries']}
        parsed = {}
        for kind, decoder in [('NOD', decode_nod), ('SGS', decode_sgs)]:
            e = entries[kind]
            parsed[kind] = decoder(data[e['offset']:e['offset']+e['size']])
        for n in parsed['NOD']['nodes']:
            if n['type'] == 0:
                assert 0 <= n['segment_index'] < parsed['SGS']['segment_count']
        save_json(OUTPUT / 'courses' / (path.stem + '.json'), {'source': path.relative_to(SOURCE).as_posix(), **parsed})
        dot = ['digraph course {', 'rankdir=LR;']
        for n in parsed['NOD']['nodes']:
            label = f"{n['index']}: type {n['type']} @ {n['offset']:#x}"
            if n['type'] == 0:
                label += f"\\nsegment {n['segment_index']} len(raw) {n['node_length_raw']}"
            dot.append(f'n{n["offset"]} [label="{label}"];')
            for i, target in enumerate(n['links']):
                dot.append(f'n{n["offset"]} -> n{target} [label="link{i}"];')
        dot.append('}')
        (OUTPUT / 'courses' / (path.stem + '.dot')).write_text('\n'.join(dot), encoding='utf-8')
        counts = Counter(c['tag'] for c in parsed['SGS']['chunks'])
        summary.append({'course': path.stem, 'nodes': parsed['NOD']['count'],
                        'segments': parsed['SGS']['segment_count'],
                        'reachable_nodes': parsed['NOD']['all_nodes_reachable'],
                        'chunk_counts': dict(counts),
                        'path_samples': sum(c['count_field'] for c in parsed['SGS']['chunks'] if c['tag']=='RPTH'),
                        'bytes_fully_accounted': True})
    save_json(OUTPUT / 'course_summary.json', summary)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()

