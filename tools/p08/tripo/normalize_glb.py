"""Normalize technical GLB JSON metadata into a fresh derived artifact.

Raw inputs, every BIN byte, geometry, transforms, UVs, material channels and
embedded image bytes are preserved. Standard glTF names and known technical
fields inside extras are renamed/removed. Copyright/license/attribution notices
are retained and flagged for review; this tool does not transfer rights, assign
authorship, detect or remove pixel steganography, or approve production art.

Unknown provider/task identifiers outside the supported metadata fields reject
normalization. PNG/JPEG ancillary metadata is inspected, never edited. Sources:
https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc
https://www.w3.org/TR/png-3/
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import zlib


ROOT = Path(__file__).resolve().parents[3]
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
MAX_GLB_BYTES = 768 * 1024 * 1024
MAX_TEXT_BYTES = 256 * 1024
GENERATOR = "RacingBois GLB metadata normalizer 1"
LOCAL_KEYS = {"racingBoisAssetId", "metadataNormalizationVersion"}
NAMED_COLLECTIONS = {"accessors", "animations", "buffers", "bufferViews", "cameras", "images",
                     "materials", "meshes", "nodes", "samplers", "scenes", "skins", "textures"}
TECHNICAL_EXTRA_KEYS = {"taskid", "tripotaskid", "jobid", "requestid", "generationid", "provider",
                        "sourceprovider", "generationprovider", "generator", "tripo", "tripometadata"}
RIGHTS_KEYS = {"copyright", "license", "licence", "attribution", "rights", "rightsholder", "disclaimer"}
RIGHTS_TEXT = re.compile(r"copyright|©|all\s+rights\s+reserved|licensed\s+under|\bCC[- ]BY\b|\bSPDX[-:]", re.I)
PROVIDER_TEXT = re.compile(r"\btripo(?:3d|[_ -]ai)?\b|tripo3d\.(?:ai|com)", re.I)
TASK_TEXT = re.compile(r"\btask[_-][A-Za-z0-9_-]{3,}|\btsk_[A-Za-z0-9_-]{3,}|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
COMPONENTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
SHAPES = {"SCALAR": (1, 1), "VEC2": (1, 2), "VEC3": (1, 3), "VEC4": (1, 4),
          "MAT2": (2, 2), "MAT3": (3, 3), "MAT4": (4, 4)}


class NormalizationError(Exception):
    """Constant nonsecret diagnostic; raw names/metadata never enter errors."""


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise NormalizationError("The JSON contains unsupported or nonfinite values.") from None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise NormalizationError("Duplicate JSON keys are not supported.")
        result[key] = value
    return result


def _invalid_constant(value):
    raise NormalizationError("Nonfinite JSON values are not supported.")


def parse_glb(raw: bytes) -> tuple[dict, bytes]:
    if len(raw) < 20 or len(raw) > MAX_GLB_BYTES:
        raise NormalizationError("GLB size is invalid.")
    magic, version, total = struct.unpack_from("<4sII", raw)
    if magic != b"glTF" or version != 2 or total != len(raw):
        raise NormalizationError("GLB header/version/length is invalid.")
    cursor = 12
    chunks = []
    while cursor < len(raw):
        if cursor + 8 > len(raw):
            raise NormalizationError("GLB chunk header is truncated.")
        length, kind = struct.unpack_from("<II", raw, cursor)
        cursor += 8
        if length % 4 or cursor + length > len(raw):
            raise NormalizationError("GLB chunk size/alignment is invalid.")
        chunks.append((kind, raw[cursor:cursor + length]))
        cursor += length
    if not chunks or chunks[0][0] != JSON_CHUNK or len(chunks) > 2 or (len(chunks) == 2 and chunks[1][0] != BIN_CHUNK):
        raise NormalizationError("Only a JSON chunk and one optional BIN chunk are supported.")
    try:
        document = json.loads(chunks[0][1].decode("utf-8"), object_pairs_hook=_pairs,
                              parse_constant=_invalid_constant)
    except (ValueError, UnicodeError):
        raise NormalizationError("GLB JSON is invalid.") from None
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise NormalizationError("A glTF2.0 asset document is required.")
    canonical(document)  # Includes overflowed float literals such as 1e999.
    binary = chunks[1][1] if len(chunks) == 2 else b""
    buffers = document.get("buffers", [])
    if not isinstance(buffers, list) or len(buffers) > 1:
        raise NormalizationError("Only the GLB embedded buffer is supported.")
    if buffers:
        buffer = buffers[0]
        length = buffer.get("byteLength")
        if type(length) is not int or length < 0 or buffer.get("uri") is not None or not 0 <= len(binary) - length <= 3:
            raise NormalizationError("Embedded buffer length or resource binding is invalid.")
    elif binary:
        raise NormalizationError("BIN data lacks an embedded buffer declaration.")
    return document, binary


def encode_glb(document: dict, binary: bytes) -> bytes:
    text = canonical(document)
    text += b" " * (-len(text) % 4)
    body = struct.pack("<II", len(text), JSON_CHUNK) + text
    if binary:
        if len(binary) % 4:
            raise NormalizationError("BIN chunk must retain its original four-byte alignment.")
        body += struct.pack("<II", len(binary), BIN_CHUNK) + binary
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body


def _token(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def safe_pointer(path: tuple) -> str:
    parts = []
    for token in path:
        token = str(token)
        if len(token) <= 64 and re.fullmatch(r"[A-Za-z0-9_]+", token) and not (PROVIDER_TEXT.search(token) or TASK_TEXT.search(token)):
            parts.append(token)
        else:
            parts.append("keysha256_" + digest(token.encode("utf-8"))[:16])
    return "/" + "/".join(parts)


def _rights(key, value) -> bool:
    return bool(value and (_token(str(key)) in RIGHTS_KEYS or
                           (isinstance(value, str) and RIGHTS_TEXT.search(value))))


def _notice(path, value) -> dict:
    return {"path": safe_pointer(path), "sha256": digest(canonical(value)),
            "characters": len(value) if isinstance(value, str) else None, "retained": True}


def _name_path(path: tuple) -> bool:
    return len(path) == 3 and path[0] in NAMED_COLLECTIONS and type(path[1]) is int and path[2] == "name"


def semantic_projection(document: dict) -> dict:
    """Remove only the metadata fields this tool is allowed to change."""
    projected = copy.deepcopy(document)
    def visit(value, path=(), in_extras=False):
        if isinstance(value, dict):
            for key in list(value):
                here = path + (key,)
                if here == ("asset", "generator") or _name_path(here) or (in_extras and (key == "name" or _token(key) in TECHNICAL_EXTRA_KEYS)) or (path == ("asset", "extras") and key in LOCAL_KEYS):
                    del value[key]
                else:
                    visit(value[key], here, in_extras or key == "extras")
            # An empty extras object has no core rendering meaning and can be
            # introduced by the local asset ID or emptied by technical cleanup.
            if value.get("extras") == {}:
                del value["extras"]
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + (index,), in_extras)
    visit(projected)
    return projected


def normalize_document(document: dict, asset_id: str) -> tuple[dict, dict]:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,63}", asset_id) or PROVIDER_TEXT.search(asset_id) or TASK_TEXT.search(asset_id):
        raise NormalizationError("The local asset ID is invalid or contains a provider/task identifier.")
    result = copy.deepcopy(document)
    changes = []
    notices = []
    scanned = 0
    def visit(value, path=(), in_extras=False):
        nonlocal scanned
        if isinstance(value, dict):
            for key in list(value):
                child = value[key]
                here = path + (key,)
                if isinstance(child, str):
                    scanned += 1
                if _rights(key, child):
                    notices.append(_notice(here, child))
                    continue
                if here == ("asset", "generator"):
                    changes.append({"path": safe_pointer(here), "action": "technical_generator_replaced",
                                    "beforeSha256": digest(canonical(child))})
                    value[key] = GENERATOR
                elif _name_path(here) or (in_extras and key == "name"):
                    name = asset_id + "_Name_" + str(len(changes)).zfill(4)
                    changes.append({"path": safe_pointer(here), "action": "technical_name_replaced",
                                    "beforeSha256": digest(canonical(child))})
                    value[key] = name
                elif in_extras and _token(key) in TECHNICAL_EXTRA_KEYS:
                    # A nested provider object might itself contain a notice.
                    nested_notices = rights_notices(child, here)
                    if nested_notices:
                        notices.extend(nested_notices)
                        continue
                    changes.append({"path": safe_pointer(here), "action": "technical_extra_removed",
                                    "beforeSha256": digest(canonical(child))})
                    del value[key]
                else:
                    visit(child, here, in_extras or key == "extras")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + (index,), in_extras)
        elif isinstance(value, str):
            scanned += 1
    visit(result)
    result["asset"].setdefault("generator", GENERATOR)
    extras = result["asset"].setdefault("extras", {})
    if not isinstance(extras, dict):
        raise NormalizationError("Asset extras must be an object for a local asset ID.")
    extras.update(racingBoisAssetId=asset_id, metadataNormalizationVersion=1)
    leftovers = identifiers(result)
    notices = rights_notices(document)
    if notices != rights_notices(result):
        raise NormalizationError("A copyright/license/attribution notice changed; normalization is rejected.")
    if digest(canonical(semantic_projection(document))) != digest(canonical(semantic_projection(result))):
        raise NormalizationError("Semantic JSON changed outside the permitted metadata fields.")
    # Rights notices are deliberately exempt from provider cleanup; retaining a
    # notice means the derived model still needs review, rather than claiming it
    # is free of attribution or that copyright has changed hands.
    return result, {"stringsVisited": scanned, "changes": changes, "rightsNotices": notices,
                    "residualIdentifiers": leftovers, "localAssetId": asset_id}


def rights_notices(value, path=()) -> list[dict]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            here = path + (key,)
            if _rights(key, child):
                found.append(_notice(here, child))
            else:
                found.extend(rights_notices(child, here))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(rights_notices(child, path + (index,)))
    elif isinstance(value, str) and RIGHTS_TEXT.search(value):
        found.append(_notice(path, value))
    return found


def identifiers(value, path=()) -> list[dict]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            here = path + (key,)
            if _rights(key, child):
                continue
            if PROVIDER_TEXT.search(key) or TASK_TEXT.search(key):
                found.append({"path": safe_pointer(here), "location": "key", "sha256": digest(key.encode("utf-8"))})
            found.extend(identifiers(child, here))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(identifiers(child, path + (index,)))
    elif isinstance(value, str) and not RIGHTS_TEXT.search(value) and (PROVIDER_TEXT.search(value) or TASK_TEXT.search(value)):
        found.append({"path": safe_pointer(path), "location": "value", "sha256": digest(value.encode("utf-8"))})
    return found


def _view(document, binary: bytes, index: int) -> tuple[int, int, dict]:
    try:
        if type(index) is not int or index < 0:
            raise ValueError
        view = document["bufferViews"][index]
        start, length = view.get("byteOffset", 0), view["byteLength"]
        declared = document["buffers"][0]["byteLength"]
        if view.get("buffer") != 0 or type(start) is not int or type(length) is not int or start < 0 or length < 0 or start + length > min(declared, len(binary)):
            raise ValueError
        return start, length, view
    except (KeyError, IndexError, TypeError, ValueError):
        raise NormalizationError("A buffer view is out of bounds or unsupported.") from None


def _layout(component_type, shape):
    try:
        fmt, size = COMPONENTS[component_type]
        columns, rows = SHAPES[shape]
    except (KeyError, TypeError):
        raise NormalizationError("Accessor component type or shape is unsupported.") from None
    column_stride = rows * size
    if columns > 1:
        column_stride += -column_stride % 4
    offsets = [column * column_stride + row * size for column in range(columns) for row in range(rows)]
    return fmt, size, offsets, columns * column_stride


def decoded_accessors(document: dict, binary: bytes) -> list[dict]:
    """Decode all core accessors, including normalized ints, sparse and MAT padding."""
    if any(extension in document.get("extensionsUsed", []) for extension in ("KHR_draco_mesh_compression", "EXT_meshopt_compression")):
        raise NormalizationError("Compressed accessor decoding requires a separate verified decoder.")
    results = []
    for index, accessor in enumerate(document.get("accessors", [])):
        count = accessor.get("count")
        if type(count) is not int or not 0 < count <= MAX_GLB_BYTES // 8:
            raise NormalizationError("Accessor count is invalid.")
        component = accessor.get("componentType")
        fmt, size, offsets, element_size = _layout(component, accessor.get("type"))
        components = len(offsets)
        element_reader = struct.Struct("<" + fmt * components) if offsets == list(range(0, components * size, size)) else None
        scalar_reader = struct.Struct("<" + fmt)
        normalized = accessor.get("normalized", False)
        if type(normalized) is not bool or (normalized and component in (5125, 5126)):
            raise NormalizationError("Accessor normalization is invalid.")
        def row(start):
            values = element_reader.unpack_from(binary, start) if element_reader else tuple(scalar_reader.unpack_from(binary, start + offset)[0] for offset in offsets)
            if normalized:
                divisor = {5120: 127, 5121: 255, 5122: 32767, 5123: 65535}[component]
                values = tuple(max(-1.0, value / divisor) for value in values)
            if any(not math.isfinite(value) for value in values):
                raise NormalizationError("Accessor data contains nonfinite values.")
            return values
        start = 0
        stride = element_size
        offset = accessor.get("byteOffset", 0)
        if type(offset) is not int or offset < 0 or offset % size:
            raise NormalizationError("Accessor byte offset is invalid.")
        if "bufferView" in accessor:
            base, length, view = _view(document, binary, accessor["bufferView"])
            stride = view.get("byteStride", element_size)
            if type(stride) is not int or stride < element_size or stride % size or offset + (count - 1) * stride + (element_size if count else 0) > length:
                raise NormalizationError("Accessor stride or bounds are invalid.")
            start = base + offset
        elif offset:
            raise NormalizationError("A zero-initialized accessor cannot have a byte offset.")
        sparse_rows = {}
        sparse = accessor.get("sparse")
        if sparse is not None:
            sparse_count = sparse.get("count")
            if type(sparse_count) is not int or not 0 < sparse_count <= count:
                raise NormalizationError("Sparse accessor count is invalid.")
            indices, values = sparse.get("indices", {}), sparse.get("values", {})
            sparse_component = indices.get("componentType")
            if sparse_component not in (5121, 5123, 5125):
                raise NormalizationError("Sparse indices must be unsigned integers.")
            sparse_fmt, sparse_size = COMPONENTS[sparse_component]
            ibase, ilength, iview = _view(document, binary, indices.get("bufferView"))
            vbase, vlength, vview = _view(document, binary, values.get("bufferView"))
            io, vo = indices.get("byteOffset", 0), values.get("byteOffset", 0)
            if type(io) is not int or type(vo) is not int or io < 0 or vo < 0 or io % sparse_size or vo % size or "byteStride" in iview or "byteStride" in vview or io + sparse_count * sparse_size > ilength or vo + sparse_count * element_size > vlength:
                raise NormalizationError("Sparse accessor bounds or alignment are invalid.")
            prior = -1
            for n in range(sparse_count):
                target = struct.unpack_from("<" + sparse_fmt, binary, ibase + io + n * sparse_size)[0]
                if not prior < target < count:
                    raise NormalizationError("Sparse indices are not unique ascending in-range indices.")
                prior = target
                sparse_rows[target] = row(vbase + vo + n * element_size)
        accumulator = hashlib.sha256()
        writer = struct.Struct("<" + "d" * components)
        zero = (0,) * components
        for n in range(count):
            values = sparse_rows.get(n)
            if values is None:
                values = row(start + n * stride) if "bufferView" in accessor else zero
            accumulator.update(writer.pack(*values))
        results.append({"index": index, "count": count, "type": accessor["type"],
                        "componentType": component, "normalized": normalized,
                        "decodedSha256": accumulator.hexdigest(), "decodedComponents": count * components})
    return results


def _text_summary(data: bytes, *, encoding="latin-1", keyword: bytes | None = None) -> dict:
    limited = len(data) > MAX_TEXT_BYTES
    text = data[:MAX_TEXT_BYTES].decode(encoding, errors="replace")
    label = (keyword or b"").decode("latin-1", errors="replace")
    return {"bytes": len(data), "sha256": digest(data), "keywordSha256": digest(keyword) if keyword is not None else None,
            "scanLimited": limited, "rightsNoticePossible": bool(_token(label) in RIGHTS_KEYS or RIGHTS_TEXT.search(text)),
            "providerIdentifierPossible": bool(PROVIDER_TEXT.search(text) or TASK_TEXT.search(text)), "retained": True}


def _inflate_text(raw: bytes) -> bytes:
    try:
        reader = zlib.decompressobj()
        data = reader.decompress(raw, MAX_TEXT_BYTES + 1)
        if not reader.eof or reader.unused_data or len(data) > MAX_TEXT_BYTES:
            raise NormalizationError("Compressed texture metadata exceeds the inspection limit or is invalid.")
        return data
    except zlib.error:
        raise NormalizationError("Compressed texture metadata is invalid.") from None


def inspect_png(raw: bytes) -> dict:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise NormalizationError("Embedded PNG signature is invalid.")
    cursor = 8
    chunks = []
    metadata = []
    width = height = None
    ended = False
    while cursor < len(raw):
        if cursor + 12 > len(raw):
            raise NormalizationError("Embedded PNG chunk is truncated.")
        length = struct.unpack_from(">I", raw, cursor)[0]
        kind = raw[cursor + 4:cursor + 8]
        if cursor + 12 + length > len(raw) or not re.fullmatch(b"[A-Za-z]{4}", kind):
            raise NormalizationError("Embedded PNG chunk bounds/type are invalid.")
        payload = raw[cursor + 8:cursor + 8 + length]
        crc = struct.unpack_from(">I", raw, cursor + 8 + length)[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise NormalizationError("Embedded PNG CRC is invalid.")
        name = kind.decode("ascii")
        chunks.append(name)
        if kind == b"IHDR":
            if width is not None or length != 13 or len(chunks) != 1:
                raise NormalizationError("Embedded PNG header is invalid.")
            width, height = struct.unpack_from(">II", payload)
        elif kind in (b"tEXt", b"zTXt", b"iTXt"):
            try:
                keyword, remainder = payload.split(b"\0", 1)
                if not 1 <= len(keyword) <= 79:
                    raise ValueError
                encoding = "latin-1"
                if kind == b"zTXt":
                    if not remainder or remainder[0] != 0:
                        raise ValueError
                    remainder = _inflate_text(remainder[1:])
                elif kind == b"iTXt":
                    compressed, method = remainder[0], remainder[1]
                    if compressed not in (0, 1) or method != 0:
                        raise ValueError
                    _, _, remainder = remainder[2:].split(b"\0", 2)
                    remainder = _inflate_text(remainder) if compressed else remainder
                    encoding = "utf-8"
                metadata.append({"chunk": name, **_text_summary(remainder, encoding=encoding, keyword=keyword)})
            except (ValueError, IndexError):
                raise NormalizationError("Embedded PNG text metadata is invalid.") from None
        elif kind in (b"eXIf", b"iCCP", b"tIME", b"pHYs"):
            metadata.append({"chunk": name, **_text_summary(payload)})
        cursor += 12 + length
        if kind == b"IEND":
            if length != 0 or cursor != len(raw):
                raise NormalizationError("Embedded PNG trailer is invalid.")
            ended = True
            break
    if not ended or width is None or "IDAT" not in chunks:
        raise NormalizationError("Embedded PNG lacks required chunks.")
    return {"format": "PNG", "width": width, "height": height, "chunks": chunks,
            "technicalMetadata": metadata, "bytesChanged": False,
            "steganography": "not assessed; metadata inspection does not detect pixel steganography"}


def inspect_jpeg(raw: bytes) -> dict:
    if not raw.startswith(b"\xff\xd8"):
        raise NormalizationError("Embedded JPEG signature is invalid.")
    cursor = 2
    markers = []
    metadata = []
    width = height = None
    ended = False
    while cursor < len(raw):
        if raw[cursor] != 0xFF:
            raise NormalizationError("Embedded JPEG marker structure is invalid.")
        while cursor < len(raw) and raw[cursor] == 0xFF:
            cursor += 1
        if cursor >= len(raw):
            raise NormalizationError("Embedded JPEG marker is truncated.")
        marker = raw[cursor]
        cursor += 1
        markers.append(f"FF{marker:02X}")
        if marker == 0xD9:
            ended = cursor == len(raw)
            break
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            continue
        if cursor + 2 > len(raw):
            raise NormalizationError("Embedded JPEG segment is truncated.")
        length = struct.unpack_from(">H", raw, cursor)[0]
        if length < 2 or cursor + length > len(raw):
            raise NormalizationError("Embedded JPEG segment bounds are invalid.")
        payload = raw[cursor + 2:cursor + length]
        if 0xE0 <= marker <= 0xEF or marker == 0xFE:
            summary = _text_summary(payload)
            # TIFF Copyright tag8298 may contain an ASCII notice without a word
            # such as 'copyright'; preserve/flag its presence conservatively.
            if marker == 0xE1 and payload.startswith(b"Exif\0\0"):
                summary["exifPresent"] = True
                summary["rightsNoticePossible"] |= b"\x98\x82" in payload or b"\x82\x98" in payload
            metadata.append({"marker": f"FF{marker:02X}", **summary})
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if len(payload) < 5:
                raise NormalizationError("Embedded JPEG frame header is invalid.")
            height, width = struct.unpack_from(">HH", payload, 1)
        cursor += length
        if marker == 0xDA:
            # Traverse entropy-coded bytes without decoding/changing any pixel.
            while cursor < len(raw):
                if raw[cursor] != 0xFF:
                    cursor += 1
                    continue
                following = cursor + 1
                while following < len(raw) and raw[following] == 0xFF:
                    following += 1
                if following >= len(raw):
                    raise NormalizationError("Embedded JPEG entropy data is truncated.")
                if raw[following] == 0 or 0xD0 <= raw[following] <= 0xD7:
                    cursor = following + 1
                    continue
                break
    if not ended:
        raise NormalizationError("Embedded JPEG trailer is invalid.")
    return {"format": "JPEG", "width": width, "height": height, "markers": markers,
            "technicalMetadata": metadata, "bytesChanged": False,
            "steganography": "not assessed; metadata inspection does not detect pixel steganography"}


def inspect_images(document: dict, binary: bytes) -> list[dict]:
    images = []
    for index, image in enumerate(document.get("images", [])):
        if "uri" in image or "bufferView" not in image:
            raise NormalizationError("Image inspection requires an embedded bufferView image.")
        start, length, _ = _view(document, binary, image["bufferView"])
        raw = binary[start:start + length]
        mime = image.get("mimeType")
        if mime == "image/png":
            summary = inspect_png(raw)
        elif mime == "image/jpeg":
            summary = inspect_jpeg(raw)
        else:
            raise NormalizationError("Only embedded PNG/JPEG inspection is supported.")
        images.append({"index": index, "mimeType": mime, "bytes": len(raw), "sha256": digest(raw), **summary})
    return images


def verify_preservation(original: dict, original_binary: bytes, derived: dict, derived_binary: bytes) -> dict:
    before = digest(canonical(semantic_projection(original)))
    after = digest(canonical(semantic_projection(derived)))
    if original_binary != derived_binary or before != after:
        raise NormalizationError("BIN bytes or semantic JSON changed; the derived model is rejected.")
    original_accessors = decoded_accessors(original, original_binary)
    derived_accessors = decoded_accessors(derived, derived_binary)
    if original_accessors != derived_accessors:
        raise NormalizationError("Decoded accessor data changed; the derived model is rejected.")
    original_images = inspect_images(original, original_binary)
    derived_images = inspect_images(derived, derived_binary)
    if original_images != derived_images:
        raise NormalizationError("Embedded image bytes or metadata changed; the derived model is rejected.")
    return {"passed": True, "binBytesExact": True, "binSha256": digest(original_binary),
            "semanticJsonExact": True, "semanticJsonSha256": before,
            "decodedAccessorsExact": True, "accessors": original_accessors,
            "decodedComponentCount": sum(row["decodedComponents"] for row in original_accessors),
            "embeddedImagesExact": True, "imageInspection": original_images}


def _owned(path: Path, root: Path, *, exists=False) -> Path:
    try:
        resolved = path.resolve(strict=exists)
        if not resolved.is_relative_to(root.resolve(strict=True)):
            raise NormalizationError("All source/output/audit paths must remain inside the workspace.")
        return resolved
    except (OSError, ValueError):
        raise NormalizationError("A workspace source/output/audit path is unavailable.") from None


def _write_new(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise NormalizationError("Derived output and audit paths must be fresh.") from None


def normalize_file(source: Path, output: Path, audit_path: Path, *, asset_id: str,
                   expected_source_sha256: str | None = None, root: Path = ROOT) -> dict:
    source = _owned(source, root, exists=True)
    output = _owned(output, root)
    audit_path = _owned(audit_path, root)
    if not source.is_file() or source.suffix.lower() != ".glb" or output.suffix.lower() != ".glb" or audit_path.suffix.lower() != ".json" or source == output or output == audit_path or output.exists() or audit_path.exists():
        raise NormalizationError("A GLB input and fresh separate GLB/JSON output paths are required.")
    if source.stat().st_size > MAX_GLB_BYTES:
        raise NormalizationError("GLB input exceeds the size limit.")
    raw = source.read_bytes()
    source_hash = digest(raw)
    if expected_source_sha256 is not None and source_hash != expected_source_sha256.lower():
        raise NormalizationError("The source hash differs from the frozen expected input.")
    document, binary = parse_glb(raw)
    normalized, metadata = normalize_document(document, asset_id)
    if metadata["residualIdentifiers"]:
        raise NormalizationError("Provider/task identifiers remain outside supported technical metadata; no derived model was written.")
    derived_raw = encode_glb(normalized, binary)
    roundtrip, derived_binary = parse_glb(derived_raw)
    if roundtrip != normalized or identifiers(roundtrip):
        raise NormalizationError("Late JSON metadata verification failed; no derived model was written.")
    preservation = verify_preservation(document, binary, roundtrip, derived_binary)
    # Re-read immediately before writing, and again after rereading the written
    # output. A late mismatch is recorded as rejected rather than accepted.
    if digest(source.read_bytes()) != source_hash:
        raise NormalizationError("The raw source changed during verification; no derived model was written.")
    _write_new(output, derived_raw)
    written = output.read_bytes()
    written_document, written_binary = parse_glb(written)
    raw_source_unchanged = digest(source.read_bytes()) == source_hash
    final_ok = written == derived_raw and written_document == normalized and written_binary == binary and not identifiers(written_document) and raw_source_unchanged
    texture_review = any(entry.get("rightsNoticePossible") or entry.get("providerIdentifierPossible") or entry.get("scanLimited")
                         for image in preservation["imageInspection"] for entry in image["technicalMetadata"])
    needs_review = bool(metadata["rightsNotices"]) or texture_review
    report = {"schema": "racing-bois.glb-metadata-normalization.v1", "localAssetId": asset_id,
              "metadataNormalizationPassed": final_ok, "status": "rejected_late_mismatch" if not final_ok else ("metadata_notice_review_required" if needs_review else "metadata_normalized"),
              "productionAccepted": False, "visualAccepted": False,
              "source": {"path": source.relative_to(root.resolve()).as_posix(), "sha256": source_hash, "bytes": len(raw)},
              "derived": {"path": output.relative_to(root.resolve()).as_posix(), "sha256": digest(written), "bytes": len(written)},
              "rawSourceUnchanged": raw_source_unchanged, "metadata": metadata, "preservation": preservation,
              "rights": {"noticesRetained": True, "reviewRequired": needs_review, "authorshipAssigned": False, "rightsTransferClaimed": False},
              "texturePolicy": {"pixelsTransformed": False, "embeddedImageBytesChanged": False,
                                "technicalMetadataEdited": False, "steganographyAssessed": False, "steganographyRemoved": False,
                                "limitation": "No vendor verification or pixel watermark/steganography removal is provided."}}
    _write_new(audit_path, canonical(report) + b"\n")
    if not final_ok:
        raise NormalizationError("A late source/output mismatch rejected the derived model; inspect the retained audit.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    args = parser.parse_args()
    try:
        report = normalize_file(args.input, args.out, args.audit, asset_id=args.asset_id,
                                expected_source_sha256=args.expected_source_sha256)
        print(json.dumps({"status": report["status"], "localAssetId": report["localAssetId"],
                          "derived": report["derived"], "noticeReviewRequired": report["rights"]["reviewRequired"],
                          "binBytesExact": report["preservation"]["binBytesExact"],
                          "decodedComponentCount": report["preservation"]["decodedComponentCount"],
                          "steganographyRemoved": False}))
        return 0
    except NormalizationError as error:
        print(json.dumps({"status": "rejected", "failure": str(error)}))
        return 1
    except Exception:
        print(json.dumps({"status": "rejected", "failure": "Local normalization failed; raw inputs were not overwritten."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
