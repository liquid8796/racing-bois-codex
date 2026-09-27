using System;
using System.Collections.Generic;
using System.Linq;

namespace RacingBois.Authoring.Editor
{
    public static partial class GoldenSampleBuilder
    {
        // An import owns only the declared prefabs/materials and the metadata of
        // its explicit Unity inputs. Review floors/pipelines and other candidates
        // have separate receipts and must not invalidate this asset import.
        private static FileReceipt[] ImportedOutputSnapshot(Descriptor descriptor)
        {
            Require(descriptor != null && descriptor.assets != null && descriptor.assets.Length > 0,
                "Selected assets are required for imported output binding.");
            return descriptor.assets.SelectMany(ImportedAssetOutputPaths)
                .Select(path => path.Replace('\\', '/')).Distinct(StringComparer.Ordinal)
                .OrderBy(path => path, StringComparer.Ordinal)
                .Select(path => { ProjectPath(path, false); return FileRow(path); }).ToArray();
        }

        private static IEnumerable<string> ImportedAssetOutputPaths(AssetSpec asset)
        {
            string prefab = PrefabPath(asset);
            yield return prefab;
            yield return prefab + ".meta";
            foreach (var material in asset.materials)
            {
                string path = OutputRoot + "/Materials/" + asset.id + "_" + material.sourceName + ".mat";
                yield return path;
                yield return path + ".meta";
            }
            foreach (string input in AssetInputs(asset))
                if (input.StartsWith("Assets/", StringComparison.Ordinal))
                    // Refresh/import already completed. Missing metadata is an
                    // error, not permission to omit GUID/import-setting binding.
                    yield return input + ".meta";
        }
    }
}
