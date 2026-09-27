// Direct Unity MCP method body. Samples actual imported skinning; no persistent edits.
var original = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
var scene = UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene, UnityEditor.SceneManagement.NewSceneMode.Additive);
UnityEngine.GameObject actor = null;
UnityEngine.Mesh baked = null;
try
{
    var prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.GameObject>("Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Ash_V7R2.prefab");
    actor = (UnityEngine.GameObject)UnityEditor.PrefabUtility.InstantiatePrefab(prefab, scene);
    var model = actor.transform.Find("Model").gameObject;
    var clip = System.Linq.Enumerable.Single(RacingBois.Client.Presentation.RiderAnimationSet.Resolve(actor.transform, null), item => item.name.EndsWith("|RB_Fall", System.StringComparison.Ordinal));
    var levels = actor.GetComponent<UnityEngine.LODGroup>().GetLODs();
    var transforms = actor.GetComponentsInChildren<UnityEngine.Transform>(true);
    var positions = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(transforms, item => item.localPosition));
    var rotations = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(transforms, item => item.localRotation));
    var scales = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(transforms, item => item.localScale));
    baked = new UnityEngine.Mesh();
    System.Func<int, float> minimum = level =>
    {
        float result = float.PositiveInfinity;
        foreach (var renderer in levels[level].renderers)
        {
            var skin = renderer as UnityEngine.SkinnedMeshRenderer;
            if (skin == null) continue;
            skin.BakeMesh(baked, false);
            foreach (var vertex in baked.vertices) result = UnityEngine.Mathf.Min(result, skin.transform.TransformPoint(vertex).y);
        }
        return result;
    };
    var pure = new System.Collections.Generic.List<object>();
    var pureMinima = new[] { float.PositiveInfinity, float.PositiveInfinity, float.PositiveInfinity };
    for (int sample = 0; sample <= 144; sample++)
    {
        for (int i = 0; i < transforms.Length; i++) { transforms[i].localPosition = positions[i]; transforms[i].localRotation = rotations[i]; transforms[i].localScale = scales[i]; }
        float time = clip.length * sample / 144f;
        clip.SampleAnimation(model, time);
        for (int level = 0; level < levels.Length; level++)
        {
            float value = minimum(level); pureMinima[level] = UnityEngine.Mathf.Min(pureMinima[level], value);
            pure.Add(new { sample = sample, seconds = time, lod = level, minimumY = value });
        }
    }
    UnityEngine.Object.DestroyImmediate(actor);
    actor = (UnityEngine.GameObject)UnityEditor.PrefabUtility.InstantiatePrefab(prefab, scene);
    levels = actor.GetComponent<UnityEngine.LODGroup>().GetLODs();
    var view = actor.AddComponent<RacingBois.Client.Presentation.RiderAnimationView>();
    if (!view.Initialize(actor.transform, RacingBois.Client.Presentation.RiderAnimationSet.Resolve(actor.transform, null))) throw new System.InvalidOperationException("Actual rider animation unavailable.");
    for (int i = 0; i < 30; i++) view.Render(RacingBois.Gameplay.Definitions.RiderMode.Riding, 0, 0, i, 0, false, 0, 1f/60);
    var blend = new System.Collections.Generic.List<object>();
    var blendMinima = new[] { float.PositiveInfinity, float.PositiveInfinity, float.PositiveInfinity };
    for (int age = 0; age <= 60; age++)
    {
        view.Render(RacingBois.Gameplay.Definitions.RiderMode.Falling, 0, 0, age, 0, false, 0, 1f/60);
        for (int level = 0; level < levels.Length; level++)
        {
            float value = minimum(level); blendMinima[level] = UnityEngine.Mathf.Min(blendMinima[level], value);
            blend.Add(new { ageTicks = age, lod = level, minimumY = value });
        }
    }
    var serialized = Newtonsoft.Json.JsonConvert.SerializeObject(new { unityVersion = UnityEngine.Application.unityVersion,
        clipLengthSeconds = clip.length, frameRate = clip.frameRate, samplesPerLod = 145, rootOffset = 0,
        pureMinima = pureMinima, blendMinima = blendMinima, pure = pure, ridingToFallingBlend = blend,
        pureFloorPassed = System.Linq.Enumerable.All(pureMinima, value => value >= 0),
        blendFloorPassed = System.Linq.Enumerable.All(blendMinima, value => value >= 0), visualAccepted = false,
        scope = "Actual imported Unity BakeMesh at flat root zero. Direct clip and production RiderAnimationView transition; no terrain/contact solver, native performance or visual acceptance." }, Newtonsoft.Json.Formatting.Indented);
    System.IO.File.WriteAllText("docs/p08/golden/ash/v7r2/native-floor-probe.json", serialized);
    return "pureMinima=" + string.Join(",", pureMinima) + "; blendMinima=" + string.Join(",", blendMinima) + "; clipLength=" + clip.length;
}
finally
{
    if (baked != null) UnityEngine.Object.DestroyImmediate(baked);
    if (actor != null) UnityEngine.Object.DestroyImmediate(actor);
    UnityEditor.SceneManagement.EditorSceneManager.CloseScene(scene, true);
    if (original.IsValid() && original.isLoaded) UnityEngine.SceneManagement.SceneManager.SetActiveScene(original);
}
