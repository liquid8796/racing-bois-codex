"""Verify a transferred native offline-LAN candidate ZIP without extracting or running it."""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import struct
import zipfile
from pathlib import Path

from package_desktop_candidate import HEX, canonical_path, digest, no_links, stream_digest

PREFIX = 'RacingBois-LanHost/'
MANIFEST = PREFIX + 'package-manifest.json'
REQUIRED = {
    'RacingBois.Server.Host.exe', 'RacingBois.Server.Host.dll', 'RacingBois.Server.Host.runtimeconfig.json',
    'coreclr.dll', 'hostfxr.dll', 'hostpolicy.dll', 'System.Private.CoreLib.dll', 'e_sqlite3.dll',
    'Microsoft.AspNetCore.Server.Kestrel.Core.dll', 'launch-native-lan.ps1', 'launch-native-lan.bat', 'README.txt', 'public/README.txt',
}
PE_FILES = ('RacingBois.Server.Host.exe', 'coreclr.dll', 'hostfxr.dll', 'hostpolicy.dll', 'e_sqlite3.dll')
FORBIDDEN = {'.db', '.sqlite', '.sqlite3', '.key', '.pem', '.pfx', '.log', '.blend', '.blend1', '.blend2',
             '.db-wal', '.db-shm', '.sqlite-wal', '.sqlite-shm', '.sqlite3-wal', '.sqlite3-shm'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def read_json(source, name):
    require(source.getinfo(name).file_size <= 16 * 1024 * 1024, 'JSON evidence exceeds size limit')
    return json.loads(source.read(name).decode('utf-8-sig'), object_pairs_hook=unique_object)


def check_paths(names):
    seen = set()
    for name in names:
        canonical_path(name)
        folded = name.casefold()
        require(folded not in seen, 'Duplicate or case-colliding archive path')
        seen.add(folded)
    for name in seen:
        parts = name.split('/')
        require(not any('/'.join(parts[:end]) in seen for end in range(1, len(parts))), 'File/directory prefix collision')


def check_payload_path(name):
    canonical_path(name)
    path = Path(name)
    lower = path.name.lower()
    require(not any(lower.endswith(suffix) for suffix in FORBIDDEN) and not lower.startswith('.env')
            and not any(part.lower() in {'data', 'realm-data', 'web'} for part in path.parts),
            'Private realm/source/key or Web payload is not a native LAN distribution')


def check_pe(source, name):
    info = source.getinfo(PREFIX + name)
    with source.open(info) as stream:
        first = stream.read(64)
        require(len(first) == 64 and first[:2] == b'MZ', 'Native PE header missing: ' + name)
        offset = struct.unpack_from('<I', first, 0x3C)[0]
        require(64 <= offset <= info.file_size - 26, 'Native PE header offset invalid: ' + name)
        stream.seek(offset)
        header = stream.read(26)
        require(len(header) == 26 and header[:4] == b'PE\0\0' and struct.unpack_from('<H', header, 4)[0] == 0x8664
                and struct.unpack_from('<H', header, 24)[0] == 0x20B, 'Native binary is not x64 PE32+: ' + name)


def verify_archive(archive: Path, expected_sha256: str, expected_protocol: int | None = None,
                   expected_content_hash: str | None = None) -> dict:
    no_links(archive)
    require(isinstance(expected_sha256, str) and HEX.fullmatch(expected_sha256) and digest(archive) == expected_sha256,
            'Archive differs from the selected external SHA256')
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist(); names = [info.filename for info in infos]
        require(1 < len(infos) <= 100000 and not source.comment, 'Archive entry count or comment invalid')
        check_paths(names)
        require(names == sorted(names) and MANIFEST in names and all(name.startswith(PREFIX) for name in names),
                'Archive root/order/manifest differs from native publisher')
        for info in infos:
            require(not info.is_dir() and info.compress_type == zipfile.ZIP_STORED and not info.flag_bits & 1
                    and info.date_time == (1980, 1, 1, 0, 0, 0) and info.create_system == 3
                    and info.external_attr == (stat.S_IFREG | 0o644) << 16 and not info.comment,
                    'Archive entry has unexpected type, compression or metadata')
        manifest = read_json(source, MANIFEST)
        keys = {'schema', 'kind', 'runtime', 'realmKind', 'releaseAccepted', 'sourceSha256', 'protocolVersion', 'contentHash', 'files'}
        require(isinstance(manifest, dict) and set(manifest) == keys and type(manifest['schema']) is int and manifest['schema'] == 1
                and manifest['kind'] == 'native-lan-host-candidate' and manifest['runtime'] == 'win-x64'
                and manifest['realmKind'] == 'offline' and manifest['releaseAccepted'] is False,
                'Offline native candidate identity is invalid')
        require(isinstance(manifest['sourceSha256'], str) and HEX.fullmatch(manifest['sourceSha256'])
                and type(manifest['protocolVersion']) is int and 0 < manifest['protocolVersion'] < 2**31
                and isinstance(manifest['contentHash'], str) and 0 < len(manifest['contentHash']) <= 256,
                'Source/protocol/content identity is invalid')
        if expected_protocol is not None:
            require(type(expected_protocol) is int and expected_protocol > 0 and manifest['protocolVersion'] == expected_protocol, 'Selected protocol does not match archive')
        if expected_content_hash is not None:
            require(manifest['contentHash'] == expected_content_hash, 'Selected content hash does not match archive')
        rows = manifest['files']; require(isinstance(rows, list) and rows, 'Native file manifest is empty')
        declared = []
        for row in rows:
            require(isinstance(row, dict) and set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int and row['bytes'] >= 0
                    and isinstance(row['sha256'], str) and HEX.fullmatch(row['sha256']), 'Native file row is invalid')
            check_payload_path(row['path']); require(row['path'] != 'package-manifest.json', 'Manifest cannot register itself')
            declared.append(row['path'])
        check_paths(declared)
        require(declared == sorted(declared) and REQUIRED.issubset(declared), 'Native payload is incomplete or unordered')
        require(names == sorted([PREFIX + path for path in declared] + [MANIFEST]), 'Archive file set differs from its exact manifest')
        for row in rows:
            name = PREFIX + row['path']
            require(source.getinfo(name).file_size == row['bytes'], 'Archived file size differs: ' + row['path'])
            with source.open(name) as stream:
                require(stream_digest(stream) == row['sha256'], 'Archived file hash differs: ' + row['path'])
        runtime = read_json(source, PREFIX + 'RacingBois.Server.Host.runtimeconfig.json')
        options = runtime.get('runtimeOptions') if isinstance(runtime, dict) else None
        require(isinstance(options, dict) and not options.get('framework') and not options.get('frameworks')
                and isinstance(options.get('includedFrameworks'), list) and options['includedFrameworks'], 'Host requires an external runtime')
        for name in PE_FILES:
            check_pe(source, name)
        manifest_sha = hashlib.sha256(source.read(MANIFEST)).hexdigest()
    require(digest(archive) == expected_sha256, 'Archive changed during verification')
    return {'schema': 1, 'archiveSha256': expected_sha256, 'archiveBytes': archive.stat().st_size,
            'archiveEntries': len(infos), 'verifiedPayloadFiles': len(rows), 'packageManifestSha256': manifest_sha,
            'sourceSha256': manifest['sourceSha256'], 'protocolVersion': manifest['protocolVersion'], 'contentHash': manifest['contentHash'],
            'archiveIntegrityPassed': True, 'nativePeHeaders': 'x64 PE32+', 'realmKind': 'offline',
            'releaseAccepted': False, 'physicalLanAccepted': False,
            'scope': 'Transferred native LAN candidate archive bytes against the selected external SHA256, package identities and required binary/runtime headers. No extraction, execution, current-source revalidation or release acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--expected-protocol', type=int)
    parser.add_argument('--expected-content-hash')
    parser.add_argument('--receipt', type=Path, help='Optional fresh verification receipt; never overwrites')
    args = parser.parse_args()
    if args.receipt:
        no_links(args.receipt); require(not args.receipt.exists(), 'Verification receipt already exists')
    result = verify_archive(args.archive, args.expected_sha256, args.expected_protocol, args.expected_content_hash)
    result['verifierSha256'] = digest(Path(__file__))
    result['sharedArchiveHelpersSha256'] = digest(Path(__file__).with_name('package_desktop_candidate.py'))
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        with args.receipt.open('x', encoding='utf8') as output:
            json.dump(result, output, indent=2); output.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
