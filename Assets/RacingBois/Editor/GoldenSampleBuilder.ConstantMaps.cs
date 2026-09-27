using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        /// <summary>Only explicitly bound material roles can opt into the small constant-map contract.</summary>
        public static void ValidateConstantMapDeclarations(MaterialSpec material)
        {
            Require(material != null, "Constant-map material is missing.");
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (string role in material.constantMaps ?? Array.Empty<string>())
            {
                Require(role != null && seen.Add(role), "Duplicate or null constant-map role: " + material.sourceName);
                InputFile input;
                switch (role)
                {
                    case "baseColor": input = material.baseColor; break;
                    case "normal": input = material.normal; break;
                    case "metallicSmoothness": input = material.metallicSmoothness; break;
                    case "occlusion": input = material.occlusion; break;
                    case "emission": input = material.emission; break;
                    default: throw new InvalidOperationException("Unknown constant-map role: " + role);
                }
                Require(HasInput(input) && input.sha256 != null && input.sha256.Length == 64 && input.sha256.All(Uri.IsHexDigit),
                    "Constant-map role requires a bound input: " + material.sourceName + "/" + role);
            }
        }

        private static bool IsConstantMap(MaterialSpec material, string role) =>
            material.constantMaps != null && material.constantMaps.Contains(role, StringComparer.Ordinal);

        /// <summary>Checks the source dimensions before decoding, never an importer-resized image.</summary>
        public static void ValidateConstantPngHeader(byte[] bytes)
        {
            Require(bytes != null && bytes.Length >= 33 &&
                bytes.Take(8).SequenceEqual(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 }) &&
                bytes[8] == 0 && bytes[9] == 0 && bytes[10] == 0 && bytes[11] == 13 &&
                bytes[12] == 'I' && bytes[13] == 'H' && bytes[14] == 'D' && bytes[15] == 'R',
                "Constant map requires a PNG with a leading IHDR.");
            Require(bytes[16] == 0 && bytes[17] == 0 && bytes[18] == 0 && bytes[19] == 4 &&
                bytes[20] == 0 && bytes[21] == 0 && bytes[22] == 0 && bytes[23] == 4,
                "Constant-map source must be exactly 4 by 4 pixels.");
            // Higher bit depths can lose differences when decoded into Color32; do not accept that as constant proof.
            Require(bytes[24] == 8 && (bytes[25] == 2 || bytes[25] == 6),
                "Constant-map source must use 8-bit RGB or RGBA pixels.");
        }

        public static Color32 ValidateConstantMapPixels(int width, int height, Color32[] pixels)
        {
            Require(width == 4 && height == 4 && pixels != null && pixels.Length == 16,
                "Decoded constant map must contain exactly 4 by 4 pixels.");
            var first = pixels[0];
            Require(pixels.All(pixel => pixel.r == first.r && pixel.g == first.g && pixel.b == first.b && pixel.a == first.a),
                "Declared constant map contains differing pixels.");
            return first;
        }

        /// <summary>Decodes hash-bound source bytes independently of TextureImporter transforms; owns only the temporary decoder.</summary>
        public static Color32 ValidateConstantMapSource(InputFile file)
        {
            VerifyInput(file);
            Require(file.path.EndsWith(".png", StringComparison.OrdinalIgnoreCase), "Constant map must be a PNG source.");
            byte[] bytes = File.ReadAllBytes(ProjectPath(file.path, false));
            using (var hash = SHA256.Create())
                Require(BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").Equals(file.sha256, StringComparison.OrdinalIgnoreCase),
                    "Constant-map source changed before decoding: " + file.path);
            ValidateConstantPngHeader(bytes);
            Texture2D decoder = null;
            try
            {
                decoder = new Texture2D(4, 4, TextureFormat.RGBA32, false, true);
                Require(ImageConversion.LoadImage(decoder, bytes, false), "Unity could not decode constant-map PNG: " + file.path);
                return ValidateConstantMapPixels(decoder.width, decoder.height, decoder.GetPixels32());
            }
            finally { if (decoder != null) UnityEngine.Object.DestroyImmediate(decoder); }
        }
    }
}
