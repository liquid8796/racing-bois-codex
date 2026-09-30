"""Offline preservation controls using synthetic GLBs, never user raw assets."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

import normalize_glb as normalize


def png_chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def png_image(metadata=()):
    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) +
            b"".join(png_chunk(kind, payload) for kind, payload in metadata) +
            png_chunk(b"IDAT", zlib.compress(b"\0\x10\x20\x30\xff")) + png_chunk(b"IEND", b""))


def model_fixture(image=None):
    binary = bytearray()
    views = []
    def view(raw):
        binary.extend(b"\0" * (-len(binary) % 4))
        index = len(views)
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(raw)})
        binary.extend(raw)
        return index
    position = view(struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0))
    normal = view(struct.pack("<9f", 0, 0, 1, 0, 0, 1, 0, 0, 1))
    uv = view(struct.pack("<6f", 0, 0, 1, 0, 0, 1))
    indices = view(struct.pack("<3H", 0, 1, 2))
    image = png_image() if image is None else image
    image_view = view(image)
    doc = {"asset": {"version": "2.0", "generator": "Tripo"},
           "scene": 0, "scenes": [{"name": "task_dummy_scene", "nodes": [0]}],
           "nodes": [{"name": "Tripo task_dummy_node", "mesh": 0, "translation": [1, 2, 3],
                      "rotation": [0, 0, 0, 1], "scale": [2, 2, 2]}],
           "meshes": [{"name": "task_dummy_mesh", "extras": {"name": "Tripo source label", "task_id": "task_dummy_mesh"},
                       "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                                       "indices": 3, "material": 0, "mode": 4}]}],
           "materials": [{"name": "Tripo Material", "pbrMetallicRoughness": {
               "baseColorTexture": {"index": 0, "texCoord": 0}, "metallicFactor": 0.4, "roughnessFactor": 0.7},
               "normalTexture": {"index": 0, "scale": 0.25}, "doubleSided": True}],
           "textures": [{"name": "task_dummy_texture", "source": 0, "sampler": 0}],
           "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
           "images": [{"name": "task_dummy_map", "bufferView": image_view, "mimeType": "image/png"}],
           "bufferViews": views, "buffers": [{"byteLength": len(binary)}],
           "accessors": [{"bufferView": position, "componentType": 5126, "count": 3, "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]},
                         {"bufferView": normal, "componentType": 5126, "count": 3, "type": "VEC3"},
                         {"bufferView": uv, "componentType": 5126, "count": 3, "type": "VEC2"},
                         {"bufferView": indices, "componentType": 5123, "count": 3, "type": "SCALAR"}]}
    binary.extend(b"\0" * (-len(binary) % 4))
    return doc, bytes(binary)


class GlbNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "raw.glb"
        self.output = self.root / "derived/normalized.glb"
        self.audit = self.root / "audit/report.json"
        self.doc, self.binary = model_fixture()
        self.source.write_bytes(normalize.encode_glb(self.doc, self.binary))

    def run_normalizer(self, **kwargs):
        return normalize.normalize_file(self.source, self.output, self.audit, asset_id="RB_DUMMY_LOCAL_01",
                                        expected_source_sha256=normalize.digest(self.source.read_bytes()), root=self.root, **kwargs)

    def accessor_digest(self, values):
        return normalize.digest(struct.pack("<" + "d" * len(values), *values))

    def test_full_roundtrip_preserves_raw_bin_channels_transforms_and_decoded_accessors(self):
        raw = self.source.read_bytes()
        report = self.run_normalizer()
        self.assertEqual(self.source.read_bytes(), raw)
        derived, binary = normalize.parse_glb(self.output.read_bytes())
        self.assertEqual(binary, self.binary)
        self.assertEqual(normalize.semantic_projection(self.doc), normalize.semantic_projection(derived))
        self.assertEqual(derived["nodes"][0]["translation"], [1, 2, 3])
        self.assertEqual(derived["materials"][0]["normalTexture"], {"index": 0, "scale": 0.25})
        self.assertEqual(derived["meshes"][0]["primitives"], self.doc["meshes"][0]["primitives"])
        self.assertEqual(report["preservation"]["decodedComponentCount"], 27)
        self.assertTrue(report["preservation"]["decodedAccessorsExact"])
        self.assertEqual(report["status"], "metadata_normalized")
        self.assertFalse(report["productionAccepted"])
        self.assertFalse(report["visualAccepted"])
        self.assertEqual(derived["asset"]["extras"]["racingBoisAssetId"], "RB_DUMMY_LOCAL_01")
        self.assertFalse(normalize.identifiers(derived))
        self.assertNotIn("task_dummy", self.audit.read_text())
        self.assertNotIn("Tripo source label", self.audit.read_text())
        self.assertFalse(report["texturePolicy"]["steganographyRemoved"])
        self.assertFalse(report["texturePolicy"]["pixelsTransformed"])

    def test_semantic_mutation_is_rejected_even_when_bin_bytes_are_identical(self):
        derived, _ = normalize.normalize_document(self.doc, "RB_DUMMY_LOCAL_01")
        for collection, key, value in (("nodes", "translation", [9, 2, 3]),
                                       ("materials", "doubleSided", False)):
            with self.subTest(collection=collection):
                modified = copy.deepcopy(derived)
                modified[collection][0][key] = value
                with self.assertRaises(normalize.NormalizationError):
                    normalize.verify_preservation(self.doc, self.binary, modified, self.binary)

    def test_bin_mutation_is_rejected_even_with_identical_json(self):
        changed = bytearray(self.binary)
        changed[0] ^= 1
        with self.assertRaises(normalize.NormalizationError):
            normalize.verify_preservation(self.doc, self.binary, self.doc, bytes(changed))

    def test_copyright_license_notice_is_retained_and_never_reassigned(self):
        self.doc["asset"]["copyright"] = "Copyright Tripo, test notice only"
        self.doc["extras"] = {"license": {"identifier": "CC-BY-4.0", "terms": "Retain test attribution"},
                               "notes": ["Copyright holder test"]}
        self.source.write_bytes(normalize.encode_glb(self.doc, self.binary))
        report = self.run_normalizer()
        derived, _ = normalize.parse_glb(self.output.read_bytes())
        self.assertEqual(derived["asset"]["copyright"], self.doc["asset"]["copyright"])
        self.assertEqual(derived["extras"], self.doc["extras"])
        self.assertTrue(report["rights"]["reviewRequired"])
        self.assertEqual(report["status"], "metadata_notice_review_required")
        self.assertFalse(report["rights"]["authorshipAssigned"])
        self.assertFalse(report["rights"]["rightsTransferClaimed"])
        self.assertEqual(len(report["metadata"]["rightsNotices"]), 3)

    def test_notice_in_generator_is_retained_and_flagged(self):
        self.doc["asset"]["generator"] = "Copyright Tripo test attribution"
        normalized, report = normalize.normalize_document(self.doc, "RB_DUMMY_LOCAL_01")
        self.assertEqual(normalized["asset"]["generator"], self.doc["asset"]["generator"])
        self.assertTrue(report["rightsNotices"])

    def test_nested_technical_object_with_notice_is_retained(self):
        self.doc["extras"] = {"provider": {"license": "MIT", "copyright": "A test attribution"}}
        normalized, report = normalize.normalize_document(self.doc, "RB_DUMMY_LOCAL_01")
        self.assertEqual(normalized["extras"], self.doc["extras"])
        self.assertEqual(len(report["rightsNotices"]), 2)

    def test_unsupported_task_identifier_rejects_without_writing_any_derived_file(self):
        self.doc["extensions"] = {"EXT_test_unclassified": {"metadata": "task_dummy_unsupported"}}
        self.source.write_bytes(normalize.encode_glb(self.doc, self.binary))
        original = self.source.read_bytes()
        with self.assertRaises(normalize.NormalizationError):
            self.run_normalizer()
        self.assertEqual(self.source.read_bytes(), original)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.audit.exists())

    def test_extra_task_ids_and_provider_keys_are_removed_without_touching_unrelated_extras(self):
        self.doc["extras"] = {"taskId": "task_dummy_job", "provider": "Tripo", "recipeVersion": 7,
                               "nested": {"generator": "Tripo", "keep": "artist-authored setting"}}
        derived, report = normalize.normalize_document(self.doc, "RB_DUMMY_LOCAL_01")
        self.assertEqual(derived["extras"], {"recipeVersion": 7, "nested": {"keep": "artist-authored setting"}})
        self.assertFalse(report["residualIdentifiers"])
        self.assertEqual(normalize.semantic_projection(self.doc), normalize.semantic_projection(derived))

    def test_preexisting_outputs_source_aliases_and_outside_paths_are_rejected(self):
        outside = self.root.parent / (self.root.name + "-outside.glb")
        for output, audit in ((self.source, self.audit), (outside, self.audit), (self.output, outside.with_suffix(".json"))):
            with self.subTest(output=output):
                with self.assertRaises(normalize.NormalizationError):
                    normalize.normalize_file(self.source, output, audit, asset_id="RB_DUMMY_LOCAL_01", root=self.root)
                self.assertFalse(outside.exists())
        self.output.parent.mkdir()
        self.output.write_bytes(b"existing unrelated output")
        with self.assertRaises(normalize.NormalizationError):
            self.run_normalizer()
        self.assertEqual(self.output.read_bytes(), b"existing unrelated output")
        self.assertFalse(self.audit.exists())

    def test_frozen_source_hash_mismatch_rejects_before_any_output(self):
        with self.assertRaises(normalize.NormalizationError):
            normalize.normalize_file(self.source, self.output, self.audit, asset_id="RB_DUMMY_LOCAL_01",
                                     expected_source_sha256="0" * 64, root=self.root)
        self.assertFalse(self.output.exists())

    def test_late_metadata_mismatch_keeps_rejected_audit_and_raw_source(self):
        original = self.source.read_bytes()
        write = normalize._write_new
        def corrupt_output(path, raw):
            if path == self.output:
                document, binary = normalize.parse_glb(raw)
                document["nodes"][0]["name"] = "task_dummy_late"
                raw = normalize.encode_glb(document, binary)
            return write(path, raw)
        with patch.object(normalize, "_write_new", side_effect=corrupt_output):
            with self.assertRaises(normalize.NormalizationError):
                self.run_normalizer()
        report = json.loads(self.audit.read_text())
        self.assertEqual(report["status"], "rejected_late_mismatch")
        self.assertFalse(report["metadataNormalizationPassed"])
        self.assertFalse(report["productionAccepted"])
        self.assertTrue(report["rawSourceUnchanged"])
        self.assertEqual(self.source.read_bytes(), original)

    def test_late_external_source_change_is_rejected_without_restoring_or_overwriting_it(self):
        original = self.source.read_bytes()
        changed_elsewhere = original + b"external-change"
        write = normalize._write_new
        def external_change(path, raw):
            write(path, raw)
            if path == self.output:
                self.source.write_bytes(changed_elsewhere)
        with patch.object(normalize, "_write_new", side_effect=external_change):
            with self.assertRaises(normalize.NormalizationError):
                self.run_normalizer()
        report = json.loads(self.audit.read_text())
        self.assertEqual(report["status"], "rejected_late_mismatch")
        self.assertFalse(report["rawSourceUnchanged"])
        self.assertEqual(self.source.read_bytes(), changed_elsewhere)

    def test_strict_glb_header_chunk_duplicate_keys_and_nonfinite_json(self):
        raw = self.source.read_bytes()
        malformed = [raw[:-1], b"notGLB" * 4,
                     struct.pack("<4sII", b"glTF", 1, len(raw)) + raw[12:]]
        for text in (b'{"asset":{"version":"2.0"},"a":1,"a":2}',
                     b'{"asset":{"version":"2.0"},"a":NaN}',
                     b'{"asset":{"version":"2.0"},"a":1e999}'):
            text += b" " * (-len(text) % 4)
            body = struct.pack("<II", len(text), normalize.JSON_CHUNK) + text
            malformed.append(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
        for value in malformed:
            with self.subTest(bytes=len(value)), self.assertRaises(normalize.NormalizationError):
                normalize.parse_glb(value)

    def test_unsupported_compressed_or_external_buffers_are_rejected(self):
        for extension in ("KHR_draco_mesh_compression", "EXT_meshopt_compression"):
            modified = copy.deepcopy(self.doc)
            modified["extensionsUsed"] = [extension]
            with self.assertRaises(normalize.NormalizationError):
                normalize.decoded_accessors(modified, self.binary)
        modified = copy.deepcopy(self.doc)
        modified["buffers"][0]["uri"] = "external.bin"
        with self.assertRaises(normalize.NormalizationError):
            normalize.parse_glb(normalize.encode_glb(modified, self.binary))

    def test_float_interleaved_accessors_decode_actual_components_and_skip_padding(self):
        binary = struct.pack("<8f", 1, 2, 3, 99, 4, 5, 6, 88)
        doc = {"buffers": [{"byteLength": len(binary)}], "bufferViews": [
            {"buffer": 0, "byteLength": len(binary), "byteStride": 16}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "type": "VEC3", "count": 2}]}
        result = normalize.decoded_accessors(doc, binary)[0]
        self.assertEqual(result["decodedSha256"], self.accessor_digest((1, 2, 3, 4, 5, 6)))

    def test_signed_normalized_accessor_clamps_minimum_and_decodes_to_floats(self):
        binary = struct.pack("<4b", -128, -127, 0, 127)
        doc = {"buffers": [{"byteLength": 4}], "bufferViews": [{"buffer": 0, "byteLength": 4}],
               "accessors": [{"bufferView": 0, "componentType": 5120, "type": "VEC4", "count": 1, "normalized": True}]}
        self.assertEqual(normalize.decoded_accessors(doc, binary)[0]["decodedSha256"], self.accessor_digest((-1, -1, 0, 1)))

    def test_padded_small_component_matrices_decode_columns_without_padding(self):
        binary = bytes((1, 2, 3, 99, 4, 5, 6, 99, 7, 8, 9, 99))
        doc = {"buffers": [{"byteLength": 12}], "bufferViews": [{"buffer": 0, "byteLength": 12}],
               "accessors": [{"bufferView": 0, "componentType": 5121, "type": "MAT3", "count": 1}]}
        self.assertEqual(normalize.decoded_accessors(doc, binary)[0]["decodedSha256"], self.accessor_digest(range(1, 10)))

    def test_sparse_accessor_decodes_zero_base_and_actual_overlay(self):
        binary = b"\x01\0\0\0" + struct.pack("<3f", 5, 6, 7)
        doc = {"buffers": [{"byteLength": len(binary)}], "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 1}, {"buffer": 0, "byteOffset": 4, "byteLength": 12}],
            "accessors": [{"componentType": 5126, "type": "VEC3", "count": 3,
                           "sparse": {"count": 1, "indices": {"bufferView": 0, "componentType": 5121},
                                      "values": {"bufferView": 1}}}]}
        result = normalize.decoded_accessors(doc, binary)[0]
        self.assertEqual(result["decodedSha256"], self.accessor_digest((0, 0, 0, 5, 6, 7, 0, 0, 0)))
        doc["accessors"][0]["sparse"]["count"] = 2
        doc["bufferViews"][0]["byteLength"] = 2
        with self.assertRaises(normalize.NormalizationError):
            normalize.decoded_accessors(doc, binary)

    def test_accessor_bounds_stride_invalid_normalization_and_nonfinite_values_reject(self):
        for field, value in (("count", 0), ("count", True), ("byteOffset", 1), ("count", 99999), ("normalized", True)):
            with self.subTest(field=field, value=value):
                modified = copy.deepcopy(self.doc)
                modified["accessors"][0][field] = value
                with self.assertRaises(normalize.NormalizationError):
                    normalize.decoded_accessors(modified, self.binary)
        modified_binary = bytearray(self.binary)
        struct.pack_into("<f", modified_binary, 0, float("nan"))
        with self.assertRaises(normalize.NormalizationError):
            normalize.decoded_accessors(self.doc, bytes(modified_binary))

    def test_png_text_compressed_text_and_utf8_notices_are_inspected_and_retained(self):
        image = png_image(((b"tEXt", b"Software\0Tripo test tool"),
                           (b"zTXt", b"Copyright\0\0" + zlib.compress(b"A test holder")),
                           (b"iTXt", b"License\0\0\0\0\0" + "© test holder".encode("utf-8"))))
        self.doc, self.binary = model_fixture(image)
        self.source.write_bytes(normalize.encode_glb(self.doc, self.binary))
        report = self.run_normalizer()
        inspection = report["preservation"]["imageInspection"][0]
        self.assertEqual((inspection["width"], inspection["height"]), (1, 1))
        self.assertEqual(len(inspection["technicalMetadata"]), 3)
        self.assertTrue(report["rights"]["reviewRequired"])
        self.assertTrue(inspection["technicalMetadata"][0]["providerIdentifierPossible"])
        self.assertFalse(report["texturePolicy"]["technicalMetadataEdited"])
        self.assertFalse(report["texturePolicy"]["steganographyAssessed"])
        self.assertNotIn("Tripo test tool", self.audit.read_text())

    def test_png_bad_crc_and_oversized_compressed_metadata_are_rejected(self):
        image = bytearray(png_image())
        image[20] ^= 1
        with self.assertRaises(normalize.NormalizationError):
            normalize.inspect_png(bytes(image))
        metadata = b"Comment\0\0" + zlib.compress(b"x" * (normalize.MAX_TEXT_BYTES + 1))
        with self.assertRaises(normalize.NormalizationError):
            normalize.inspect_png(png_image(((b"zTXt", metadata),)))

    def test_jpeg_comment_exif_and_entropy_markers_are_inspected_without_modification(self):
        def segment(marker, raw):
            return bytes((0xFF, marker)) + struct.pack(">H", len(raw) + 2) + raw
        exif = b"Exif\0\0II\x2a\0\x98\x82test attribution"
        raw = (b"\xff\xd8" + segment(0xE1, exif) + segment(0xFE, b"Copyright test holder") +
               segment(0xC0, b"\x08\0\x01\0\x01\x01\x01\x11\0") +
               segment(0xDA, b"\x01\x01\0\0\x3f\0") + b"\x12\xff\0\x34\xff\xd0\x56\xff\xd9")
        original = bytes(raw)
        report = normalize.inspect_jpeg(raw)
        self.assertEqual(raw, original)
        self.assertEqual((report["width"], report["height"]), (1, 1))
        self.assertTrue(all(row["rightsNoticePossible"] for row in report["technicalMetadata"]))
        self.assertFalse(report["bytesChanged"])
        with self.assertRaises(normalize.NormalizationError):
            normalize.inspect_jpeg(raw[:-1])


if __name__ == "__main__":
    unittest.main()
