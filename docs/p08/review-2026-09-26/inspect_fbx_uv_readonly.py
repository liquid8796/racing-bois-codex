"""Read P08 FBX bytes without Blender/Unity; report UV area only, not visual acceptance."""
import json
import hashlib
from datetime import datetime, timezone
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read_fbx(path):
    data = path.read_bytes()
    if not data.startswith(b"Kaydara FBX Binary"):
        raise ValueError("Expected binary FBX")
    wide = struct.unpack_from("<I", data, 23)[0] >= 7500
    header, size = ("<QQQB", 25) if wide else ("<IIIB", 13)

    def prop(offset):
        kind = chr(data[offset])
        offset += 1
        simple = {"Y": "h", "C": "?", "I": "i", "F": "f", "D": "d", "L": "q"}
        if kind in simple:
            fmt = "<" + simple[kind]
            return struct.unpack_from(fmt, data, offset)[0], offset + struct.calcsize(fmt)
        if kind in "fdilbc":
            count, encoding, length = struct.unpack_from("<III", data, offset)
            offset += 12
            raw = data[offset:offset + length]
            raw = zlib.decompress(raw) if encoding else raw
            fmt = {"f": "f", "d": "d", "i": "i", "l": "q", "b": "?", "c": "?"}[kind]
            return list(struct.unpack("<" + fmt * count, raw)), offset + length
        if kind in "SR":
            length = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            raw = data[offset:offset + length]
            return raw.decode("utf8", "replace") if kind == "S" else raw, offset + length
        raise ValueError("Unknown FBX property " + kind)

    def node(offset):
        end, count, _, name_length = struct.unpack_from(header, data, offset)
        if end == 0:
            return None, offset + size
        offset += size
        name = data[offset:offset + name_length].decode()
        offset += name_length
        props = []
        for _ in range(count):
            value, offset = prop(offset)
            props.append(value)
        children = []
        while offset < end:
            child, offset = node(offset)
            if child is None:
                break
            children.append(child)
        return (name, props, children), end

    result, offset = [], 27
    while offset < len(data):
        entry, offset = node(offset)
        if entry is None:
            break
        result.append(entry)
    return result


def inspect(path):
    nodes = read_fbx(path)
    objects = next(n[2] for n in nodes if n[0] == "Objects")
    models = {n[1][0]: n[1][1].split("\x00")[0] for n in objects if n[0] == "Model"}
    connections = next(n[2] for n in nodes if n[0] == "Connections")
    parents = {n[1][1]: n[1][2] for n in connections if n[1][0] == "OO"}
    reports = []
    for geo in (n for n in objects if n[0] == "Geometry"):
        name = models.get(parents.get(geo[1][0]), geo[1][1])
        if "_L0_" not in name:
            continue
        entries = {n[0]: n for n in geo[2]}
        polygon_indices = entries["PolygonVertexIndex"][1][0]
        vertices = entries["Vertices"][1][0]
        uv_entries = {n[0]: n for n in entries["LayerElementUV"][2]}
        uv, indices = uv_entries["UV"][1][0], uv_entries["UVIndex"][1][0]
        if uv_entries["MappingInformationType"][1][0] != "ByPolygonVertex" or uv_entries["ReferenceInformationType"][1][0] != "IndexToDirect":
            raise ValueError("Unsupported UV mapping")
        if len(polygon_indices) != len(indices) or len(indices) % 3 or any(polygon_indices[i] >= 0 for i in range(2, len(indices), 3)):
            raise ValueError("Expected triangle list")
        areas, strip_count, mesh_area, subpixel_mesh_area = [], 0, 0., 0.
        for start in range(0, len(indices), 3):
            points = [(uv[indices[i] * 2], uv[indices[i] * 2 + 1]) for i in range(start, start + 3)]
            a, b, c = points
            area = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
            if not math.isfinite(area):
                raise ValueError("Nonfinite UV triangle")
            areas.append(area * 1024 * 1024)
            vi = [polygon_indices[i] if polygon_indices[i] >= 0 else -polygon_indices[i] - 1 for i in range(start, start + 3)]
            va, vb, vc = [vertices[i * 3:i * 3 + 3] for i in vi]
            ab, ac = [[q - p for p, q in zip(va, end)] for end in [vb, vc]]
            cross = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
            face_area = math.sqrt(sum(v * v for v in cross)) / 2
            mesh_area += face_area
            if area * 1024 * 1024 < 1:
                subpixel_mesh_area += face_area
            strip_count += all((x * 4) % 1 < .059 for x, _ in points)
        areas.sort()
        reports.append({"fbx": path.relative_to(ROOT).as_posix(), "mesh": name,
                        "triangles": len(areas), "subpixelAreaAt1024": sum(v < 1 for v in areas),
                        "subpixelAreaAt512": sum(v < 4 for v in areas),
                        "reservedRepairStripTriangles": strip_count, "minimumAreaAt1024": areas[0],
                        "medianAreaAt1024": areas[len(areas) // 2],
                        "sumTriangleUvAreaAt1024": sum(areas),
                        "geometricSurfaceFractionUnderOneTexelAt1024": subpixel_mesh_area / mesh_area})
    return reports


if __name__ == "__main__":
    paths = sorted((ROOT / "Assets/RacingBois/Art/P08").glob("*.fbx"))
    rows = [row for p in paths for row in inspect(p)]
    print(json.dumps({"scope": "Current exported LOD0 FBX UV triangles only. Subpixel area is a review signal, not an automatic defect or a pixels-per-meter measurement.",
                      "createdUtc": datetime.now(timezone.utc).isoformat(),
                      "sourceHashes": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                      "meshCount": len(rows), "triangles": sum(r["triangles"] for r in rows),
                      "subpixelAreaAt1024": sum(r["subpixelAreaAt1024"] for r in rows),
                      "subpixelAreaAt512": sum(r["subpixelAreaAt512"] for r in rows), "meshes": rows}, indent=2))
