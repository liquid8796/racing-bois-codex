"""Author the Spark V1 finish textures from original deterministic signals.

No concept pixels, borrowed texture, mesh, Blender state, or runtime files are
read or written. Locked concept files are read only to verify their identities.
Run with ordinary Python + NumPy + Pillow, outside Blender. The generated
binding snippet defines a function; importing it does not mutate a scene.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "ArtSource/P08/Golden/Spark/V1/Textures"
REFERENCES = {
    "ArtSource/Concepts/P08/Golden/spark-v1.png":
        "e358ecf1a809f5373aa45ef92cbd6897ed1e1693cacc73b0f6df697d91bedce6",
    "ArtSource/Concepts/P08/Golden/spark-v1-side.png":
        "ad5478c942350462a34d12b1ba9f9714cb00a595ff9465bc1d000cf6b5e7ad0b",
}
# Linear shader values inherited from the original Spark build, not sampled
# lit photograph/concept RGB. Entries: reflectance, metallic, roughness, size,
# UV multiplier. The original UV0 is 2 repeats per metre.
SPECS = {
    "Spark_Cream": ((.66, .595, .475), 0, .27, 4, 1),
    "Spark_Graphite": ((.028, .030, .033), .08, .39, 512, 2),
    "Spark_Machined": ((.55, .565, .59), .97, .27, 512, 8),
    "Spark_SatinSteel": ((.43, .405, .355), .97, .34, 1024, 4),
    "Spark_Rubber": ((.012, .014, .016), 0, .70, 512, 2),
    "Spark_Leather": ((.050, .024, .013), 0, .57, 1024, 1),
    "Spark_Lens": ((.91, .94, .98), 0, .035, 4, 1),
    "Spark_Lamp": ((.85, .85, .82), .08, .19, 4, 1),
    "Spark_Amber": ((.52, .13, .012), .04, .25, 4, 1),
    "Spark_RedLamp": ((.38, .005, .009), .04, .24, 4, 1),
}
INTENTS = {
    "Spark_Cream": "Warm ivory opaque coating; uniform pigment and smooth clearcoat. Tank stripe remains parent-owned Copper atlas.",
    "Spark_Graphite": "Neutral dark cast/powder-coated frame and cases; low-amplitude isotropic micro-relief, no painted highlights or dirt.",
    "Spark_Machined": "Neutral polished machined steel; fine directional tool response in roughness/normal, constant conductor reflectance.",
    "Spark_SatinSteel": "Slightly warm satin exhaust steel; denser parallel finishing marks, no baked illumination, rust or heat bands.",
    "Spark_Rubber": "Matte near-black vulcanized rubber; fine isotropic mould texture only. Tread and grip ribs must be real geometry or object-specific maps.",
    "Spark_Leather": "Dark warm-brown saddle leather; shallow rounded grain with restrained crease pigment. Saddle ribs, strap, piping and stitching are separate geometry/detail work.",
    "Spark_Lens": "Nearly clear slightly cool glass, flat tangent normal; optical ribs and lens shape are geometry-specific, not invented tiling detail.",
    "Spark_Lamp": "Neutral warm white bulb; constant emission color separated from emissive intensity.",
    "Spark_Amber": "Saturated amber lens pigment and emission color; signal timing/intensity remain runtime responsibilities.",
    "Spark_RedLamp": "Deep red rear lens pigment and emission color; brake/tail intensity remains a runtime responsibility.",
}
EMISSION_STRENGTH = {"Spark_Lamp": .15, "Spark_Amber": .25, "Spark_RedLamp": .25}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linear_to_srgb(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0, 1)
    return np.where(value <= .0031308, value * 12.92,
                    1.055 * np.power(value, 1 / 2.4) - .055)


def srgb_to_linear(value: np.ndarray) -> np.ndarray:
    return np.where(value <= .04045, value / 12.92,
                    np.power((value + .055) / 1.055, 2.4))


def byte(value: np.ndarray) -> np.ndarray:
    return np.rint(np.clip(value, 0, 1) * 255).astype(np.uint8)


def periodic_signal(size: int, frequencies: tuple[int, ...], seed: int) -> np.ndarray:
    """A band-limited isotropic manufacturing signal with exact repeat period."""
    rng = np.random.default_rng(seed)
    x = np.arange(size, dtype=np.float64)[None, :] / size
    y = np.arange(size, dtype=np.float64)[:, None] / size
    signal = np.zeros((size, size), dtype=np.float64)
    for frequency in frequencies:
        # Integer wave vectors make every term seamless. This is microscopic
        # surface variation, not random large-area stains or distressed wear.
        for _ in range(7):
            angle = rng.uniform(0, np.pi * 2)
            u, v = np.rint(np.array([np.cos(angle), np.sin(angle)]) * frequency)
            phase = rng.uniform(0, np.pi * 2)
            signal += np.sin(np.pi * 2 * (u * x + v * y) + phase)
    signal -= signal.mean()
    return signal / max(float(np.max(np.abs(signal))), 1e-9)


def brushed_signal(size: int, seed: int) -> np.ndarray:
    """Fine tool-pass variation along UV U, principally varying across V."""
    rng = np.random.default_rng(seed)
    x = np.arange(size, dtype=np.float64)[None, :] / size
    y = np.arange(size, dtype=np.float64)[:, None] / size
    signal = np.zeros((size, size), dtype=np.float64)
    for frequency, weight in [(47, .18), (89, .28), (127, .30), (179, .24)]:
        phase = rng.uniform(0, np.pi * 2)
        # Small periodic modulation avoids ruler-straight synthetic stripes.
        signal += weight * np.sin(np.pi * 2 * frequency * y + phase +
                                  .13 * np.sin(np.pi * 2 * 3 * x + phase))
    signal -= signal.mean()
    return signal / np.max(np.abs(signal))


def leather_grain(size: int) -> np.ndarray:
    """Periodic, jittered 1.95 mm grain cells in a 0.5 m tile."""
    cells = 256
    rng = np.random.default_rng(45061)
    jitter = rng.uniform(.2, .8, size=(cells, cells, 2))
    y, x = np.indices((size, size), dtype=np.float64) * cells / size
    ix, iy = x.astype(int), y.astype(int)
    first = np.full((size, size), np.inf)
    second = first.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            offsets = jitter[(iy + dy) % cells, (ix + dx) % cells]
            distance = np.hypot(ix + dx + offsets[..., 0] - x,
                                iy + dy + offsets[..., 1] - y)
            second = np.minimum(second, np.maximum(first, distance))
            first = np.minimum(first, distance)
    # Rounded plateau with narrow creases; no lighting gradient is baked in.
    creases = np.exp(-np.square((second - first) / .10))
    signal = -creases + .12 * periodic_signal(size, (191, 251), 45062)
    signal -= signal.mean()
    return signal / np.max(np.abs(signal))


def tangent_normals(height_metres: np.ndarray, tile_metres: float) -> np.ndarray:
    texel_metres = tile_metres / height_metres.shape[0]
    du = (np.roll(height_metres, -1, axis=1) - np.roll(height_metres, 1, axis=1)) / (2 * texel_metres)
    dv = (np.roll(height_metres, -1, axis=0) - np.roll(height_metres, 1, axis=0)) / (2 * texel_metres)
    # Arrays here are in UV coordinates, row zero == V zero. Storage flips
    # vertically once, so image top maps to V one in Blender/Unity.
    normal = np.stack((-du, -dv, np.ones_like(du)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return normal


def save_map(name: str, role: str, values: np.ndarray, encoding: str) -> dict:
    encoded = byte(linear_to_srgb(values) if encoding == "sRGB" else values)
    encoded = np.flipud(encoded)
    path = OUTPUT / f"{name}_{role}.png"
    Image.fromarray(encoded).save(path, optimize=True)
    with Image.open(path) as image:
        actual = np.array(image)
        mode, size = image.mode, image.size
    if not np.array_equal(actual, encoded):
        raise ValueError(f"PNG channel roundtrip failed: {path.name}")
    normalized = actual.astype(np.float64) / 255
    decoded = srgb_to_linear(normalized) if encoding == "sRGB" else normalized
    target = np.flipud(values)
    quant_error = np.abs(decoded - target)
    # The exact nearest 8-bit encoded value must already match; this range
    # additionally rejects unintended colour-space transforms on reload.
    max_error = float(quant_error.max())
    if max_error > (.00446 if encoding == "sRGB" else .5 / 255 + 1e-12):
        raise ValueError(f"Unexpected decoded quantization error: {path.name}")
    flat = decoded.reshape(-1, 1 if decoded.ndim == 2 else decoded.shape[-1])
    samples = []
    for row, col in [(0, 0), (size[1] // 2, size[0] // 2), (size[1] - 1, size[0] - 1)]:
        samples.append({"xyFromTopLeft": [col, row],
                        "storedBytes": np.atleast_1d(actual[row, col]).tolist(),
                        "decodedLinear": np.atleast_1d(decoded[row, col]).round(8).tolist()})
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path),
            "byteLength": path.stat().st_size, "mode": mode, "resolution": list(size),
            "encoding": encoding, "decodedMinimum": flat.min(axis=0).round(8).tolist(),
            "decodedMaximum": flat.max(axis=0).round(8).tolist(),
            "decodedMean": flat.mean(axis=0).round(8).tolist(),
            "maxDecodedQuantizationError": max_error, "samples": samples,
            "pngRoundtripExact": True}


def make_finish(name: str, spec: tuple) -> dict:
    color, metallic, roughness, size, uv_scale = spec
    tile = .5 / uv_scale
    height = np.zeros((size, size))
    variation = np.zeros_like(height)
    base = np.broadcast_to(color, (4, 4, 3)).copy()
    response = {"pattern": "constant", "heightPeakToPeakMicrometres": 0}
    if name in ("Spark_Graphite", "Spark_Rubber"):
        variation = periodic_signal(size, (57, 103, 167), 45021 if name.endswith("Graphite") else 45031)
        height = variation * (8e-6 if name.endswith("Graphite") else 9e-6)
        rough = roughness + variation * (.017 if name.endswith("Graphite") else .023)
        response["pattern"] = "isotropic band-limited manufacturing microtexture"
    elif name in ("Spark_Machined", "Spark_SatinSteel"):
        variation = brushed_signal(size, 45041 if name.endswith("Machined") else 45051)
        height = variation * (1.3e-6 if name.endswith("Machined") else 2.0e-6)
        rough = roughness + variation * (.018 if name.endswith("Machined") else .026)
        response["pattern"] = "parallel U-directed tool marks; roughness and shallow tangent-normal response"
        response["orientationRequirement"] = "UV U must follow the intended brushing direction; projection seams are not solved by these maps."
    elif name == "Spark_Leather":
        variation = leather_grain(size)
        height = variation * 40e-6
        rough = roughness - variation * .021
        base = np.array(color)[None, None, :] * (1 + variation[..., None] * .022)
        # Colour carries only a weak pigment difference. Downsample in LINEAR
        # light before encoding rather than wasting a 1024 colour texture.
        base = base.reshape(512, 2, 512, 2, 3).mean(axis=(1, 3))
        response["pattern"] = "rounded 1.95 mm leather grain with fine pores; 2.2 percent maximum pigment modulation"
    else:
        rough = np.full((size, size), roughness)
    response["heightPeakToPeakMicrometres"] = float(np.ptp(height) * 1e6)
    response["tileMetresAtOriginalUV0"] = tile
    response["roughnessNominal"] = roughness
    response["roughnessActualMeanBeforeQuantization"] = float(rough.mean())
    normal = tangent_normals(height, tile)
    rough_byte = byte(rough)
    # Exact complement after quantization; Blender roughness and Unity
    # smoothness can therefore never differ by a second rounding decision.
    packed = np.zeros((size, size, 4), dtype=np.uint8)
    packed[..., 0] = byte(np.array(metallic))
    packed[..., 3] = 255 - rough_byte
    maps = {
        "baseColor": save_map(name, "BaseColor", base, "sRGB"),
        "normal": save_map(name, "Normal", normal * .5 + .5, "linear-data"),
        "metallicSmoothness": save_map(name, "MetallicSmoothness", packed / 255., "linear-data"),
        "roughness": save_map(name, "Roughness", rough_byte / 255., "linear-data"),
    }
    if name in EMISSION_STRENGTH:
        maps["emission"] = save_map(name, "Emission", np.broadcast_to(color, (4, 4, 3)), "sRGB")
    actual_mask = np.array(Image.open(ROOT / maps["metallicSmoothness"]["path"]))
    actual_rough = np.array(Image.open(ROOT / maps["roughness"]["path"]))
    actual_normal = np.array(Image.open(ROOT / maps["normal"]["path"])).astype(float) / 255 * 2 - 1
    metallic_matches = bool(np.all(actual_mask[..., 0] == byte(np.array(metallic))))
    if not metallic_matches:
        raise ValueError("Packed red does not match authored metallic")
    if not np.all(actual_mask[..., 3].astype(int) + actual_rough.astype(int) == 255):
        raise ValueError("Packed smoothness is not the exact inverse roughness")
    if np.any(actual_mask[..., 1:3] != 0):
        raise ValueError("Unused packed channels must be zero")
    normal_length_error = float(np.max(np.abs(np.linalg.norm(actual_normal, axis=-1) - 1)))
    if normal_length_error > .007:
        raise ValueError("Normal map decode unexpectedly leaves the unit hemisphere")
    # Mip generation should use the normal-map importer; renormalization is
    # necessary after filtering and the tiny 8-bit neutral-XY bias is known.
    return {"material": name, "intent": INTENTS[name], "baseReflectanceLinear": list(color),
            "metallicNominal": metallic, "uvScale": uv_scale,
            "emissionStrengthBlender": EMISSION_STRENGTH.get(name, 0),
            "surfaceResponse": response, "maps": maps,
            "artifactChecks": {"packedRedIsMetallic": metallic_matches, "packedGreenBlueAreZero": True,
                               "packedAlphaPlusRoughnessEquals255": True,
                               "normalPositiveZ": bool(np.all(actual_normal[..., 2] > 0)),
                               "decodedNormalMaximumUnitLengthError": normal_length_error},
            "visualAccepted": False}


BINDING = r'''"""Staged helper, NOT run by the texture author. No scene change on import.

Parent usage in Blender, after every PNG and the manifest are fully saved:
    exec(Path(".../Textures/finish-material-binding.py").read_text())
    bind_spark_finish_materials(Path(".../Textures"))
Run before packing. This deliberately loads new image datablocks, sets their
colour space and reloads from disk. It never touches Spark_Copper or geometry.
"""
import hashlib
import json
from pathlib import Path


def bind_spark_finish_materials(texture_dir, uv_map_name="UV0_SurfaceMetres"):
    import bpy
    texture_dir = Path(texture_dir)
    intent = json.loads((texture_dir / "finish-surface-intent.json").read_text())
    entries = intent["finishes"]
    if len(entries) != 10 or any(item["material"] == "Spark_Copper" for item in entries):
        raise RuntimeError("Unexpected finish binding scope")
    # Verify the whole staged set before changing any material.
    for entry in entries:
        material = bpy.data.materials.get(entry["material"])
        if not material or not material.use_nodes:
            raise RuntimeError("Missing existing material: " + entry["material"])
        if not any(node.type == 'BSDF_PRINCIPLED' for node in material.node_tree.nodes):
            raise RuntimeError("Missing Principled shader: " + entry["material"])
        for artifact in entry["maps"].values():
            path = texture_dir / Path(artifact["path"]).name
            if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
                raise RuntimeError("Stale or incomplete texture: " + str(path))
    bound = []
    for entry in entries:
        material = bpy.data.materials[entry["material"]]
        tree = material.node_tree
        shader = next(node for node in tree.nodes if node.type == 'BSDF_PRINCIPLED')
        for node in list(tree.nodes):
            if node.get("sparkFinishBinding", False):
                tree.nodes.remove(node)

        def node(kind, name):
            result = tree.nodes.new(kind)
            result.name = name
            result.label = name
            result["sparkFinishBinding"] = True
            return result

        uv = node('ShaderNodeUVMap', 'Spark finish authored UV')
        uv.uv_map = uv_map_name
        uv.location = (-1000, 0)
        scale = node('ShaderNodeVectorMath', 'Spark finish metric repeat')
        scale.operation = 'SCALE'
        scale.inputs['Scale'].default_value = entry['uvScale']
        scale.location = (-800, 0)
        tree.links.new(uv.outputs['UV'], scale.inputs[0])
        textures = {}
        for index, (role, artifact) in enumerate(entry['maps'].items()):
            path = texture_dir / Path(artifact['path']).name
            image = bpy.data.images.load(str(path), check_existing=False)
            image.colorspace_settings.name = 'sRGB' if artifact['encoding'] == 'sRGB' else 'Non-Color'
            image.alpha_mode = 'CHANNEL_PACKED' if role == 'metallicSmoothness' else 'NONE'
            image.reload()
            texture = node('ShaderNodeTexImage', 'Spark finish ' + role)
            texture.image = image
            texture.interpolation = 'Linear'
            texture.extension = 'REPEAT'
            texture.location = (-560, 330 - 230 * index)
            tree.links.new(scale.outputs['Vector'], texture.inputs['Vector'])
            textures[role] = texture
        tree.links.new(textures['baseColor'].outputs['Color'], shader.inputs['Base Color'])
        channels = node('ShaderNodeSeparateColor', 'Spark R metallic')
        channels.mode = 'RGB'
        channels.location = (-200, -130)
        tree.links.new(textures['metallicSmoothness'].outputs['Color'], channels.inputs['Color'])
        tree.links.new(channels.outputs['Red'], shader.inputs['Metallic'])
        tree.links.new(textures['roughness'].outputs['Color'], shader.inputs['Roughness'])
        normal = node('ShaderNodeNormalMap', 'Spark tangent normal +Y')
        normal.space = 'TANGENT'
        normal.uv_map = uv_map_name
        normal.inputs['Strength'].default_value = 1
        normal.location = (-200, -390)
        tree.links.new(textures['normal'].outputs['Color'], normal.inputs['Color'])
        tree.links.new(normal.outputs['Normal'], shader.inputs['Normal'])
        if 'emission' in textures:
            tree.links.new(textures['emission'].outputs['Color'], shader.inputs['Emission Color'])
            shader.inputs['Emission Strength'].default_value = entry['emissionStrengthBlender']
        material['sparkFinishIntent'] = entry['intent']
        material['sparkFinishVisualAccepted'] = False
        material['sparkFinishBindingVersion'] = 1
        bound.append(entry['material'])
    return {'boundMaterials': bound, 'imagesLoadedFreshAndReloaded': True,
            'copperTouched': False, 'visualAccepted': False}
'''


def main() -> None:
    for relative, expected in REFERENCES.items():
        if sha(ROOT / relative) != expected:
            raise ValueError("Locked reference identity changed: " + relative)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Parent is concurrently authoring Copper. Do not enumerate, rewrite,
    # clean up or assert stable hashes for that separate ownership scope.
    finishes = [make_finish(name, spec) for name, spec in SPECS.items()]
    binding_path = OUTPUT / "finish-material-binding.py"
    binding_path.write_text(BINDING, encoding="utf-8", newline="\n")
    # Compile-only validation; never imports bpy or executes the helper.
    compile(BINDING, str(binding_path), "exec")
    total_bytes = sum(artifact['byteLength'] for entry in finishes for artifact in entry['maps'].values())
    manifest = {
        "schemaVersion": 1, "asset": "Spark 450 V1 finishes, one bike", "visualAccepted": False,
        "originalProceduralPixels": True, "conceptPixelsCopied": False,
        "borrowedTexturesOrMeshes": False, "sceneOrRuntimeModified": False,
        "primaryReference": next(iter(REFERENCES)), "sideReferenceIsUncalibrated": True,
        "lockedReferences": REFERENCES,
        "authoringScript": {"path": Path(__file__).relative_to(ROOT).as_posix(), "sha256": sha(Path(__file__))},
        "colorIntent": "Base/emission PNG RGB is explicit IEC sRGB encoding of linear shader reflectance. Do not gamma-decode normal, packed metallic/smoothness or roughness.",
        "normalConvention": "Tangent-space OpenGL +Y, normalized before RGB8 encoding; image top corresponds to UV V=1; renormalize after filtering.",
        "packedChannelSemantics": {"R": "metallic, linear UNORM8", "G": "unused zero", "B": "unused zero", "A": "smoothness = 1 - roughness, linear UNORM8; NOT opacity"},
        "importIntent": {"baseAndEmission": "sRGB enabled; RGB, no transparency", "normal": "Normal map importer, tangent +Y, non-colour; generate normal-aware mips", "metallicSmoothness": "sRGB disabled; preserve alpha; alphaIsTransparency false; never premultiply", "roughness": "Single-channel linear data for Blender; Unity uses mask alpha", "wrap": "Repeat", "filter": "Trilinear in game, mipmaps enabled", "desktopCompression": "BC5 normal and BC7 colour/packed where available; inspect compressed result before acceptance. No Unity importer is changed by this tool."},
        "ownership": {"copperAndGeometry": "parent; untouched", "runtime": "frozen; untouched"},
        "knownLimits": [
            "Procedural finish candidates are not captured or measured material BRDFs; matching actual renderer, lighting, scale and concept remains unverified.",
            "Original projected UV0 overlaps intentionally for repeated material response. Island orientation and visible projection seams need mesh/renderer inspection, especially directional metals.",
            "One shared Graphite response spans cast cases, frame tubes and fenders. Material splitting may be needed if their target gloss differs visibly.",
            "Shared Machined response cannot simultaneously provide physically correct circular brake machining, straight fork polishing and optical mirrors. Author object-specific UVs or separate finishes if comparison requires it.",
            "Glass transmission, headlamp flutes, amber reflector prisms, stitching, seat ribs, rubber tread and exhaust heat bands are not supplied by these generic finish maps.",
            "No Unity import, Blender render, LOD appearance, texture-compression inspection or final concept-fidelity acceptance is claimed.",
        ],
        "finishes": finishes, "pngCount": sum(len(entry['maps']) for entry in finishes),
        "totalPngBytes": total_bytes,
        "bindingSnippet": {"path": binding_path.relative_to(ROOT).as_posix(), "sha256": sha(binding_path), "executed": False, "syntaxCompiledOnly": True},
    }
    intent_path = OUTPUT / "finish-surface-intent.json"
    intent_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"finishes": len(finishes), "pngCount": manifest['pngCount'],
                      "totalPngBytes": total_bytes, "manifest": str(intent_path),
                      "manifestSha256": sha(intent_path), "visualAccepted": False}))


if __name__ == "__main__":
    main()
