using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.Networking;

namespace RacingBois.Client.Adapters
{
    /// <summary>Single-owner bounded content loading from the installed root or an explicitly configured origin.</summary>
    public sealed class P08ContentLoader : MonoBehaviour
    {
        public const long MaximumBundleBytes = ContentManifestRules.MaximumBundleBytes;
        public event Action Changed;
        public event Action BeforeRouteUnload;
        public event Action<int> Ready;
        public event Action<string,string,bool,float> MusicRequested;
        public bool Busy { get; private set; }
        public string Error { get; private set; } = "";
        public string Status { get; private set; } = "";
        public float Progress { get; private set; }
        public int RequestedCourse { get; private set; } = -1;
        public int LoadedCourse => ContentRegistry.Route == null ? -1 : ContentRegistry.Route.CourseIndex;
        public long DownloadedBytes { get; private set; }
        private Uri contentBase;
        private P08ContentManifest manifest;
        private readonly Dictionary<string,P08BundleEntry> entries = new Dictionary<string,P08BundleEntry>(StringComparer.Ordinal);
        private AssetBundle actorsBundle, routeBundle;
        private AssetBundleCreateRequest creating;
        private UnityWebRequest downloading;
        private int queuedCourse = -1;
        private bool destroyed, failed;

        public void Configure(string editorBaseUrl = "", DesktopRuntimeConfig desktopConfig = null)
        {
            if (Busy || manifest != null) throw new InvalidOperationException("Content base cannot change after loading.");
#if UNITY_WEBGL && !UNITY_EDITOR
            Uri page;
            if (Uri.TryCreate(UnityEngine.Application.absoluteURL,UriKind.Absolute,out page) && (page.Scheme == "http" || page.Scheme == "https"))
                contentBase = new Uri(page.GetLeftPart(UriPartial.Authority) + "/Content/");
#else
            contentBase = DesktopConfiguration.ContentBase(desktopConfig, editorBaseUrl);
#endif
            if (contentBase == null || (contentBase.Scheme != "https" && contentBase.Scheme != "http" && !contentBase.IsFile))
                throw new InvalidOperationException("Không xác định được nguồn tải nội dung trò chơi.");
        }
        public bool IsReady(int course) => !Busy && !failed && Error.Length == 0 && ContentRegistry.ReadyFor(course);
        public void RequestCourse(int course)
        {
            if (!CampaignCatalog.IsPlayableRoute(course)) { Fail("Đường đua này chưa có gói nội dung sẵn sàng."); return; }
            if (contentBase == null) Configure();
            RequestedCourse = course;
            if (IsReady(course)) { Guard(() => Ready?.Invoke(course)); return; }
            queuedCourse = course;
            if (!Busy) StartCoroutine(LoadQueue());
        }
        public string ResolveMusicUrl(string id)
        {
            if (string.IsNullOrEmpty(id) || !entries.TryGetValue(id,out var entry) || entry.kind != "music") return "";
            return BundleUri(entry.url).AbsoluteUri;
        }
        public void Retry() { if (!Busy && RequestedCourse >= 0) RequestCourse(RequestedCourse); }
        private IEnumerator LoadQueue()
        {
            Busy = true;
            while (queuedCourse >= 0 && !destroyed)
            {
                int course = queuedCourse; queuedCourse = -1; failed = false; Error = ""; Progress = 0;
                Status = "Đang kiểm tra gói nội dung…"; Changed?.Invoke();
                if (manifest == null) yield return LoadManifest();
                if (failed) break;
                if (ContentRegistry.Actors == null)
                {
                    Status = "Đang tải xe và tay đua…"; Changed?.Invoke();
                    yield return LoadBundle(entries[manifest.actorsId], value => actorsBundle = value);
                    if (failed) break;
                    var actorRequest = actorsBundle.LoadAssetAsync<P08ActorContent>(entries[manifest.actorsId].asset);
                    yield return actorRequest;
                    if (!Guard(() => ContentRegistry.SetActors(actorRequest.asset as P08ActorContent))) { actorsBundle.Unload(true); actorsBundle = null; break; }
                }
                if (ContentRegistry.ReadyFor(course)) continue;
                BeforeRouteUnload?.Invoke(); ContentRegistry.ClearRoute();
                // Views detach/destroy route objects in the callback. Give deferred Unity destruction one frame before unloading dependencies.
                yield return null;
                if (routeBundle != null) { routeBundle.Unload(true); routeBundle = null; }
                Status = "Đang tải " + CampaignCatalog.GetRoute(course).DisplayName + "…"; Changed?.Invoke();
                P08BundleEntry routeEntry = null;
                if (!Guard(() => { routeEntry = entries["route-" + course]; if (routeEntry.courseIndex != course || routeEntry.kind != "route") throw new InvalidDataException(); })) break;
                yield return LoadBundle(routeEntry,value => routeBundle = value);
                if (failed) break;
                var routeRequest = routeBundle.LoadAssetAsync<P08RouteContent>(routeEntry.asset); yield return routeRequest;
                var route = routeRequest.asset as P08RouteContent;
                if (!Guard(() => { if (route == null) throw new InvalidDataException(); route.Validate(course); })) break;
                P08BundleEntry musicEntry = null;
                if (!Guard(() => { musicEntry = entries[route.RouteMusicId]; if (musicEntry.kind != "music") throw new InvalidDataException(); })) break;
                string musicUrl = BundleUri(musicEntry.url).AbsoluteUri;
                if (!Guard(() => ContentRegistry.SetRoute(route,musicEntry.id,musicUrl))) break;
                // One hashed stream is requested at a time; platform adapters own playback and decoding.
                MusicRequested?.Invoke(musicEntry.id,musicUrl,true,.077f);
                if (queuedCourse >= 0 && queuedCourse != course) continue;
                Progress = 1; Status = "Nội dung đã sẵn sàng.";
            }
            Busy = false; Changed?.Invoke();
            if (!failed && !destroyed && ContentRegistry.ReadyFor(RequestedCourse)) Guard(() => Ready?.Invoke(RequestedCourse));
        }
        private IEnumerator LoadManifest()
        {
            using (var request = UnityWebRequest.Get(new Uri(contentBase,"manifest.json")))
            {
                downloading = request; request.timeout = 30; var operation = request.SendWebRequest();
                while (!operation.isDone) { if (request.downloadedBytes > 131072) { request.Abort(); break; } yield return null; }
                downloading = null;
                if (request.result != UnityWebRequest.Result.Success || request.downloadedBytes > 131072) { Fail("Không tải được danh mục nội dung. Hãy kiểm tra kết nối và thử lại."); yield break; }
                Guard(() =>
                {
                    var parsed = JsonUtility.FromJson<P08ContentManifest>(request.downloadHandler.text);
#if UNITY_WEBGL && !UNITY_EDITOR
                    const string expectedTarget = "WebGL";
#else
                    const string expectedTarget = "StandaloneWindows64";
#endif
                    var validated = ContentManifestRules.Validate(parsed,GameplayRules.ContentHash,contentBase,expectedTarget);
                    entries.Clear();foreach (var pair in validated) entries.Add(pair.Key,pair.Value);
                    manifest = parsed;
                });
            }
        }
        private IEnumerator LoadBundle(P08BundleEntry entry, Action<AssetBundle> completed)
        {
            byte[] bytes;
            using (var request = UnityWebRequest.Get(BundleUri(entry.url)))
            {
                downloading = request; request.timeout = 60; var operation = request.SendWebRequest();
                while (!operation.isDone)
                {
                    Progress = Mathf.Clamp01(request.downloadedBytes / (float)entry.bytes);
                    if (request.downloadedBytes > (ulong)entry.bytes) { request.Abort(); break; }
                    yield return null;
                }
                downloading = null;
                if (request.result != UnityWebRequest.Result.Success || request.downloadedBytes != (ulong)entry.bytes)
                { Fail("Tải nội dung bị gián đoạn. Hãy thử lại."); yield break; }
                bytes = request.downloadHandler.data;
            }
            if (!Guard(() =>
            {
                using (var sha = SHA256.Create())
                {
                    string digest = BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","");
                    if (!string.Equals(digest,entry.sha256,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException();
                }
            })) yield break;
            DownloadedBytes += bytes.LongLength;
            if (!Guard(() => creating = AssetBundle.LoadFromMemoryAsync(bytes,entry.crc))) yield break;
            yield return creating;
            var bundle = creating.assetBundle; creating = null; bytes = null;
            if (bundle == null) { Fail("Gói nội dung bị lỗi hoặc không phù hợp phiên bản này."); yield break; }
            completed(bundle);
        }
        private Uri BundleUri(string relative) => ContentManifestRules.BundleUri(contentBase,relative);
        private bool Guard(Action action)
        { try { action(); return true; } catch (Exception error) { Debug.LogWarning("P08 content validation: " + error.GetType().Name); Fail("Nội dung chưa sẵn sàng hoặc khác phiên bản trò chơi. Hãy khởi động lại hoặc thử lại."); return false; } }
        private void Fail(string message) { failed = true; ContentRegistry.ClearRoute(); Error = Status = message; Changed?.Invoke(); }
        private void OnDestroy()
        {
            destroyed = true; downloading?.Abort();
            if (creating != null) { var pending = creating; pending.completed += _ => { if (pending.assetBundle != null) pending.assetBundle.Unload(true); }; }
            ContentRegistry.Clear();
            if (routeBundle != null) routeBundle.Unload(true); if (actorsBundle != null) actorsBundle.Unload(true);
        }
    }
}
