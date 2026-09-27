// Execute this method body through direct Unity MCP while the Editor is idle.
// Temporary studio infrastructure only; no scene or project asset is saved.
const string prefabPath = "Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Spark_v1.prefab";
const string output = "docs/p08/golden/spark/v1/unity-studio-20260927-02";
if (UnityEditor.EditorApplication.isPlayingOrWillChangePlaymode || UnityEditor.EditorApplication.isCompiling)
    throw new System.InvalidOperationException("Editor must be idle.");
if (System.IO.Directory.Exists(output)) throw new System.InvalidOperationException("Fresh capture directory required.");
var prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.GameObject>(prefabPath);
if (prefab == null) throw new System.InvalidOperationException("Imported Spark prefab required.");
var original = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
var oldLights = UnityEngine.Object.FindObjectsByType<UnityEngine.Light>(UnityEngine.FindObjectsSortMode.None);
var lightStates = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(oldLights, light => light.enabled));
var scene = UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene, UnityEditor.SceneManagement.NewSceneMode.Additive);
UnityEngine.Material floorMaterial = null;
try
{
    UnityEngine.SceneManagement.SceneManager.SetActiveScene(scene);
    for (int i = 0; i < oldLights.Length; i++) oldLights[i].enabled = false;
    var actor = (UnityEngine.GameObject)UnityEditor.PrefabUtility.InstantiatePrefab(prefab, scene);
    var origin = new UnityEngine.Vector3(0, 1000, 0);
    actor.transform.position = origin;
    var lod = actor.GetComponent<UnityEngine.LODGroup>();
    lod.ForceLOD(0);
    var renderers = lod.GetLODs()[0].renderers;
    // Renderer.bounds may not yet reflect a newly instantiated Editor object's world transform.
    var bounds = new UnityEngine.Bounds(origin, UnityEngine.Vector3.zero);
    foreach (var renderer in renderers)
        foreach (var vertex in renderer.GetComponent<UnityEngine.MeshFilter>().sharedMesh.vertices)
            bounds.Encapsulate(renderer.transform.TransformPoint(vertex));
    var camera = new UnityEngine.GameObject("Owned Spark studio camera").AddComponent<UnityEngine.Camera>();
    camera.clearFlags = UnityEngine.CameraClearFlags.SolidColor;
    camera.backgroundColor = new UnityEngine.Color(.16f, .17f, .18f);
    camera.nearClipPlane = .03f; camera.farClipPlane = 50; camera.fieldOfView = 38; camera.aspect = 1.5f;
    var floor = UnityEngine.GameObject.CreatePrimitive(UnityEngine.PrimitiveType.Plane);
    floor.name = "Owned diagnostic floor"; floor.transform.position = origin + new UnityEngine.Vector3(0, -.012f, 0);
    floor.transform.localScale = new UnityEngine.Vector3(2, 1, 2);
    UnityEngine.Object.DestroyImmediate(floor.GetComponent<UnityEngine.Collider>());
    floorMaterial = new UnityEngine.Material(UnityEngine.Shader.Find("Universal Render Pipeline/Lit"));
    floorMaterial.SetColor("_BaseColor", new UnityEngine.Color(.20f, .21f, .22f));
    floorMaterial.SetFloat("_Smoothness", .15f); floor.GetComponent<UnityEngine.Renderer>().sharedMaterial = floorMaterial;
    var rotations = new[] { new UnityEngine.Vector3(38,-32,0), new UnityEngine.Vector3(30,115,0), new UnityEngine.Vector3(15,190,0) };
    var intensities = new[] { 2.2f, .65f, 1.15f };
    for (int i = 0; i < rotations.Length; i++)
    {
        var light = new UnityEngine.GameObject("Owned studio light " + i).AddComponent<UnityEngine.Light>();
        light.type = UnityEngine.LightType.Directional; light.intensity = intensities[i];
        light.transform.rotation = UnityEngine.Quaternion.Euler(rotations[i]);
        light.shadows = i == 0 ? UnityEngine.LightShadows.Soft : UnityEngine.LightShadows.None;
    }
    UnityEngine.RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
    UnityEngine.RenderSettings.ambientLight = new UnityEngine.Color(.36f, .38f, .42f);
    UnityEngine.RenderSettings.fog = false;
    System.IO.Directory.CreateDirectory(output);
    var rows = new System.Collections.Generic.List<object>();
    var directions = new[] { new UnityEngine.Vector3(1,.42f,1.25f), new UnityEngine.Vector3(1,.08f,0), new UnityEngine.Vector3(0,.12f,-1), new UnityEngine.Vector3(1,.42f,1.25f) };
    var names = new[] { "quarter-lod0", "side-lod0", "rear-lod0", "quarter-lod2" };
    float distance = bounds.size.magnitude * .5f / UnityEngine.Mathf.Sin(19 * UnityEngine.Mathf.Deg2Rad) * 1.12f;
    for (int i = 0; i < names.Length; i++)
    {
        lod.ForceLOD(i == 3 ? 2 : 0);
        camera.transform.position = bounds.center + directions[i].normalized * distance;
        camera.transform.LookAt(bounds.center);
        UnityEngine.Texture2D texture = null;
        var target = UnityEngine.RenderTexture.GetTemporary(1536, 1024, 24, UnityEngine.RenderTextureFormat.ARGB32, UnityEngine.RenderTextureReadWrite.sRGB);
        var previousTarget = UnityEngine.RenderTexture.active;
        try
        {
            var request = new UnityEngine.Rendering.Universal.UniversalRenderPipeline.SingleCameraRequest { destination = target };
            if (!UnityEngine.Rendering.RenderPipeline.SupportsRenderRequest(camera, request)) throw new System.InvalidOperationException("Explicit URP capture unavailable.");
            UnityEngine.Rendering.RenderPipeline.SubmitRenderRequest(camera, request);
            UnityEngine.RenderTexture.active = target;
            texture = new UnityEngine.Texture2D(1536, 1024, UnityEngine.TextureFormat.RGBA32, false, false);
            texture.ReadPixels(new UnityEngine.Rect(0, 0, 1536, 1024), 0, 0); texture.Apply(false, false);
            var pixels = texture.GetPixels32(); bool varied = false;
            for (int p = 31; p < pixels.Length; p += 31)
                if (System.Math.Abs(pixels[p].r-pixels[0].r)+System.Math.Abs(pixels[p].g-pixels[0].g)+System.Math.Abs(pixels[p].b-pixels[0].b)>20) { varied=true; break; }
            if (!varied) throw new System.InvalidOperationException("Unusable uniform frame; bounds center=" + bounds.center + "; camera=" + camera.transform.position);
            byte[] bytes = UnityEngine.ImageConversion.EncodeToPNG(texture);
            string path = output + "/" + names[i] + ".png";
            System.IO.File.WriteAllBytes(path, bytes);
            string sha; using (var hash = System.Security.Cryptography.SHA256.Create()) sha = System.BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
            rows.Add(new { path = path, sha256 = sha, lod = i == 3 ? 2 : 0, width = 1536, height = 1024,
                cameraRelative = new[] { camera.transform.position.x-origin.x, camera.transform.position.y-origin.y, camera.transform.position.z-origin.z }, fieldOfView = camera.fieldOfView });
        }
        finally
        {
            UnityEngine.RenderTexture.active = previousTarget;
            UnityEngine.RenderTexture.ReleaseTemporary(target);
            if (texture != null) UnityEngine.Object.DestroyImmediate(texture);
        }
    }
    var receipt = Newtonsoft.Json.JsonConvert.SerializeObject(new { captures = rows, unityVersion = UnityEngine.Application.unityVersion,
        prefab = prefabPath, graphicsApi = UnityEngine.SystemInfo.graphicsDeviceType.ToString(), visualAccepted = false,
        scope = "Actual Editor URP camera renders in a temporary neutral studio. No game release, native player, calibrated concept lighting or visual acceptance." }, Newtonsoft.Json.Formatting.Indented);
    System.IO.File.WriteAllText(output + "/capture.json", receipt);
    return receipt;
}
finally
{
    UnityEditor.SceneManagement.EditorSceneManager.CloseScene(scene, true);
    if (floorMaterial != null) UnityEngine.Object.DestroyImmediate(floorMaterial);
    for (int i = 0; i < oldLights.Length; i++) if (oldLights[i] != null) oldLights[i].enabled = lightStates[i];
    if (original.IsValid() && original.isLoaded) UnityEngine.SceneManagement.SceneManager.SetActiveScene(original);
}
