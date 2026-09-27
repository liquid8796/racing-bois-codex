// Execute this method body through direct Unity MCP while the Editor is idle.
// Temporary studio infrastructure only; no scene or project asset is saved.
const string prefabPath = "Assets/RacingBois/Golden/Generated/Prefabs/RB_Golden_Apex_r5.prefab";
const string output = "docs/p08/promotion/captures/apex-r5-continuation04";
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
    camera.transform.position = bounds.center + new UnityEngine.Vector3(1,.42f,1.25f).normalized * (bounds.size.magnitude * .5f / UnityEngine.Mathf.Sin(19 * UnityEngine.Mathf.Deg2Rad) * 1.12f);
    camera.transform.LookAt(bounds.center);
    var receipt = RacingBois.Authoring.Editor.GoldenProductionCapture.Capture("docs/p08/golden/apex/r5/descriptor.json", "RB_Golden_Apex_r5", "docs/p08/golden/unity/import-4d1286bf9e05493d84785e737fa89f4f.json", actor, camera, "quarter", "Locked apex-v2 hero three-quarter motorcycle view; neutral studio lighting differs", output + "/quarter.png", 1536, 1024);
    return receipt;
}
finally
{
    UnityEditor.SceneManagement.EditorSceneManager.CloseScene(scene, true);
    if (floorMaterial != null) UnityEngine.Object.DestroyImmediate(floorMaterial);
    for (int i = 0; i < oldLights.Length; i++) if (oldLights[i] != null) oldLights[i].enabled = lightStates[i];
    if (original.IsValid() && original.isLoaded) UnityEngine.SceneManagement.SceneManager.SetActiveScene(original);
}


