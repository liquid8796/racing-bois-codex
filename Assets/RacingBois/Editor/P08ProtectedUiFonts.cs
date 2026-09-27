using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
using UnityEngine.TextCore.Text;
using Object = UnityEngine.Object;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Read-only snapshots. No font mutation, save, reimport, cloning or restoration.</summary>
    internal sealed class P08ProtectedUiFonts
    {
        internal static readonly string[] Paths = {
            "Assets/RacingBois/UI/Fonts/NotoSans-Regular SDF.asset",
            "Assets/RacingBois/UI/Fonts/NotoSans-ExtraBold SDF.asset"
        };
        internal sealed class Member
        {
            public string type, name, guid, memorySha256, pixelsSha256;
            public long localId;
            public bool dirty, readable;
            public int hideFlags, width, height, format, mipmaps;
        }
        internal sealed class FontRecord
        {
            public string path, guid, fileSha256, metaSha256;
            public Member[] members;
        }
        private sealed class State { internal FontRecord Record; internal Object[] Objects; }
        private readonly State[] states;
        internal FontRecord[] Before => states.Select(value => value.Record).ToArray();
        internal bool Contains(Object value) => states.Any(state => state.Objects.Contains(value));

        internal P08ProtectedUiFonts(string privateBackupDirectory, IEnumerable<string> capturedPaths = null)
        {
            states = (capturedPaths ?? Paths).Select(path =>
            {
                // Production captures the actual checked-out font bytes. A diagnostic run may
                // separately pin user-owned hashes; those are not a clean-checkout prerequisite.
                var objects = AssetDatabase.LoadAllAssetsAtPath(path);
                Need(objects.OfType<FontAsset>().Count() == 1 && objects.All(value => value is FontAsset || value is Material || value is Texture2D), "unexpected_protected_font_members");
                var record = new FontRecord { path = path, guid = AssetDatabase.AssetPathToGUID(path), fileSha256 = FileHash(path), metaSha256 = FileHash(path + ".meta"),
                    members = objects.Select(Capture).OrderBy(value => value.localId).ToArray() };
                return new State { Record = record, Objects = objects };
            }).ToArray();
            // Generated owned fonts need the same immutable memory/pixel contract, but
            // no user-data recovery backup. Original fonts always supply a private path.
            if (privateBackupDirectory == null) { Verify(); return; }
            Directory.CreateDirectory(privateBackupDirectory);
            foreach (var state in states)
            {
                string prefix = Path.Combine(privateBackupDirectory, state.Record.guid);
                WriteNew(prefix + ".asset", File.ReadAllBytes(state.Record.path));
                WriteNew(prefix + ".asset.meta", File.ReadAllBytes(state.Record.path + ".meta"));
                foreach (var value in state.Objects)
                {
                    long id = LocalId(value);
                    WriteNew(prefix + "." + id + ".memory.json", Encoding.UTF8.GetBytes(EditorJsonUtility.ToJson(value)));
                    if (value is Texture2D texture) WriteNew(prefix + "." + id + ".pixels.bin", texture.GetRawTextureData<byte>().ToArray());
                }
            }
            Verify();
        }

        internal void Verify()
        {
            foreach (var state in states)
            {
                var before = state.Record;
                Need(FileHash(before.path) == before.fileSha256 && FileHash(before.path + ".meta") == before.metaSha256 &&
                    AssetDatabase.AssetPathToGUID(before.path) == before.guid, "protected_font_bytes_or_guid_changed:" + before.path);
                var current = AssetDatabase.LoadAllAssetsAtPath(before.path);
                Need(current.Length == state.Objects.Length && state.Objects.All(value => value != null && current.Contains(value)), "protected_font_object_identity_changed:" + before.path);
                var members = current.Select(Capture).OrderBy(value => value.localId).ToArray();
                Need(JsonConvert.SerializeObject(members) == JsonConvert.SerializeObject(before.members), "protected_font_memory_or_pixels_changed:" + before.path);
            }
        }
        private static Member Capture(Object value)
        {
            Need(value != null && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string _, out long _), "font_member_identity_unavailable");
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string guid, out long localId);
            var result = new Member { type = value.GetType().FullName, name = value.name, guid = guid, localId = localId,
                dirty = EditorUtility.IsDirty(value), hideFlags = (int)value.hideFlags, memorySha256 = TextHash(EditorJsonUtility.ToJson(value)) };
            if (value is Texture2D texture)
            {
                Need(texture.isReadable, "protected_font_cpu_pixels_unavailable");
                result.readable = true; result.width = texture.width; result.height = texture.height; result.format = (int)texture.format; result.mipmaps = texture.mipmapCount;
                result.pixelsSha256 = BytesHash(texture.GetRawTextureData<byte>().ToArray());
            }
            return result;
        }
        internal static long LocalId(Object value)
        { Need(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string _, out long id), "asset_local_id_unavailable"); return id; }
        internal static string FileHash(string path) { using (var file = File.OpenRead(path)) using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(file)); }
        internal static string TextHash(string value) => BytesHash(Encoding.UTF8.GetBytes(value));
        internal static string BytesHash(byte[] value) { using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(value)); }
        private static string Hex(byte[] value) => BitConverter.ToString(value).Replace("-", "").ToLowerInvariant();
        internal static void WriteNew(string path, byte[] data) { using (var file = new FileStream(path, FileMode.CreateNew, FileAccess.Write)) file.Write(data, 0, data.Length); }
        internal static void Need(bool value, string message) { if (!value) throw new InvalidOperationException(message); }
    }
}
