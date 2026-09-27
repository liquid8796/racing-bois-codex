using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        [Serializable] public sealed class GeometryProbeCase
        { public string name; public bool expectedAccepted, actualAccepted, passed; }
        [Serializable] public sealed class GeometryProbeReceipt
        { public string utc, validatorSha256; public bool passed; public GeometryProbeCase[] cases; }

        /// <summary>Runs the real native validator with equivalent unit encodings and deliberately invalid geometry.</summary>
        public static string ProbePhysicalGeometryUnits()
        {
            VerifyCompiledSources();
            var cases = new List<GeometryProbeCase>();
            GeometryProbe(cases, "metre-encoded-centimetre-triangle", .01f, Vector3.one, Vector3.zero, false, true);
            GeometryProbe(cases, "same-physical-triangle-scale100", .0001f, Vector3.one * 100, Vector3.zero, false, true);
            GeometryProbe(cases, "same-physical-triangle-scale001", 1f, Vector3.one * .01f, Vector3.zero, false, true);
            GeometryProbe(cases, "tiny-physical-triangle-rejected", .001f, Vector3.one * .001f, Vector3.zero, false, false);
            GeometryProbe(cases, "collinear-triangle-rejected", .01f, Vector3.one * 100, Vector3.zero, true, false);
            GeometryProbe(cases, "nonuniform-valid-transform", .0001f, new Vector3(100, .5f, 2), Vector3.zero, false, true);
            GeometryProbe(cases, "collapsed-transform-rejected", .01f, new Vector3(0, 1, 1), Vector3.zero, false, false);
            GeometryProbe(cases, "large-translation-does-not-change-area", .01f, Vector3.one, Vector3.one * 10000000, false, true);
            var receipt = new GeometryProbeReceipt
            {
                utc = DateTime.UtcNow.ToString("O"), validatorSha256 = Digest("Assets/RacingBois/Editor/GoldenSampleBuilder.Validation.cs"),
                passed = cases.TrueForAll(item => item.passed), cases = cases.ToArray()
            };
            string json = JsonUtility.ToJson(receipt, true);
            Directory.CreateDirectory(ReceiptRoot); File.WriteAllText(ReceiptRoot + "/geometry-unit-controls.json", json);
            Require(receipt.passed, "A native geometry-unit regression failed.");
            return json;
        }

        private static void GeometryProbe(List<GeometryProbeCase> cases, string name, float side, Vector3 scale,
            Vector3 translation, bool collinear, bool expected)
        {
            var mesh = new Mesh { name = name };
            try
            {
                mesh.vertices = new[] { Vector3.zero, new Vector3(side, 0, 0), collinear ? new Vector3(side * 2, 0, 0) : new Vector3(0, side, 0) };
                mesh.normals = new[] { Vector3.forward, Vector3.forward, Vector3.forward };
                mesh.tangents = new[] { new Vector4(1, 0, 0, 1), new Vector4(1, 0, 0, 1), new Vector4(1, 0, 0, 1) };
                mesh.uv = new[] { Vector2.zero, Vector2.right, Vector2.up }; mesh.triangles = new[] { 0, 1, 2 };
                bool accepted = true;
                try { ValidateMesh(mesh, 1, name, Matrix4x4.TRS(translation, Quaternion.identity, scale)); }
                catch (InvalidOperationException error)
                {
                    // A negative fixture must fail the physical-area gate, not an unrelated precondition.
                    if (!error.Message.StartsWith("Degenerate triangle in physical metres:", StringComparison.Ordinal)) throw;
                    accepted = false;
                }
                cases.Add(new GeometryProbeCase { name = name, expectedAccepted = expected, actualAccepted = accepted, passed = expected == accepted });
            }
            finally { UnityEngine.Object.DestroyImmediate(mesh); }
        }
    }
}
