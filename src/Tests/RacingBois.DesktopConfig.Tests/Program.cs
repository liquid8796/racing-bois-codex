using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text.Json;
using RacingBois.Client.Application;

var tests = new List<object>(); int failed = 0;
void Check(bool condition) { if (!condition) throw new InvalidOperationException("Assertion failed"); }
void Reject(Action action) { try { action(); } catch (ArgumentException) { return; } throw new InvalidOperationException("Invalid config accepted"); }
void Test(string name, Action action) { try { action(); tests.Add(new { name, passed = true }); Console.WriteLine("PASS " + name); } catch (Exception error) { failed++; tests.Add(new { name, passed = false, error = error.Message }); Console.WriteLine("FAIL " + name + ": " + error.Message); } }
string install = Path.GetFullPath(Path.Combine("_local", "Installed Racing Bois", "RacingBois_Data", "StreamingAssets"));
var local = DesktopRuntimeConfigRules.ContentBase(new DesktopRuntimeConfig(), install, false);
string hashedSong = "audio/race." + new string('a',64) + ".ogg";
Test("standalone_content_resolves_installed_streaming_assets_without_page_url", () => {
    Check(local.IsFile && Path.GetFullPath(local.LocalPath).TrimEnd(Path.DirectorySeparatorChar) == Path.Combine(install,"Content"));
    Check(!local.LocalPath.Contains("Content-editor"));
});
Test("editor_root_is_distinct_from_installed_root", () => {
    var editor = DesktopRuntimeConfigRules.ContentBase(new DesktopRuntimeConfig(), install, true);
    Check(editor.IsFile && editor.LocalPath.TrimEnd(Path.DirectorySeparatorChar) == Path.GetFullPath("Build/Content-editor"));
});
Test("default_endpoint_explicitly_identifies_local_lan_host", () => {
    Check(DesktopRuntimeConfigRules.BackendEndpoint(new DesktopRuntimeConfig()) == "ws://127.0.0.1:7777/multiplayer");
    Reject(() => DesktopRuntimeConfigRules.BackendEndpoint(new DesktopRuntimeConfig{ connectionMode="online" }));
});
Test("online_endpoint_and_content_origin_are_independent_and_require_trusted_https_wss", () => {
    var config = new DesktopRuntimeConfig {connectionMode="online",backendWebSocketUrl="wss://play.example/multiplayer",contentBaseUrl="https://cdn.example/racing/content"};
    Check(DesktopRuntimeConfigRules.BackendEndpoint(config) == "wss://play.example/multiplayer");
    Check(DesktopRuntimeConfigRules.ContentBase(config,install,false).AbsoluteUri == "https://cdn.example/racing/content/");
    config.contentBaseUrl="";
    Check(DesktopRuntimeConfigRules.ContentBase(config,install,false).IsFile && DesktopRuntimeConfigRules.BackendEndpoint(config)=="wss://play.example/multiplayer");
    config.backendWebSocketUrl="ws://play.example/multiplayer"; Reject(()=>DesktopRuntimeConfigRules.BackendEndpoint(config));
    foreach(string invalid in new[]{"http://cdn.example/Content/","file:///C:/outside/","https://user:secret@cdn.example/","https://cdn.example/?token=x","https://cdn.example/#fragment","https://cdn.example/%2e%2e/","https://cdn.example/\\outside"})
        Reject(()=>DesktopRuntimeConfigRules.RemoteContentBase(invalid,false));
});
Test("malformed_config_and_non_ws_backend_are_rejected", () => {
    Reject(()=>DesktopRuntimeConfigRules.BackendEndpoint(new DesktopRuntimeConfig {schema=2}));
    Reject(()=>DesktopRuntimeConfigRules.BackendEndpoint(new DesktopRuntimeConfig {connectionMode="other"}));
    foreach(string endpoint in new[]{"https://play.example/multiplayer","wss://user:pass@play.example/multiplayer","wss://play.example/other","wss://play.example/multiplayer?token=x","wss://play.example/multiplayer#frag"})
        Reject(()=>DesktopRuntimeConfigRules.BackendEndpoint(new DesktopRuntimeConfig {backendWebSocketUrl=endpoint}));
});
Test("editor_http_override_is_loopback_only_and_never_applies_to_standalone", () => {
    Check(DesktopRuntimeConfigRules.ContentBase(new DesktopRuntimeConfig(),install,true,"http://127.0.0.1:7777/Content").Scheme == "http");
    Reject(()=>DesktopRuntimeConfigRules.RemoteContentBase("http://remote.example/Content",true));
    Check(DesktopRuntimeConfigRules.ContentBase(new DesktopRuntimeConfig(),install,false,"http://127.0.0.1:7777/Content").IsFile);
});
Test("installed_music_accepts_spaces_and_rejects_outside_content_root", () => {
    var music = new Uri(local,hashedSong);
    Check(music.AbsoluteUri.Contains("%20") && DesktopMusicUrlRules.TryValidate(music.AbsoluteUri,local,out var normalized) && normalized == music.AbsoluteUri);
    foreach(string value in new[]{new Uri(local,"../outside/"+hashedSong).AbsoluteUri,new Uri(local,"../Content-other/"+hashedSong).AbsoluteUri,new Uri(local,"audio/plain.ogg").AbsoluteUri,local.AbsoluteUri+"audio/bad%00."+new string('a',64)+".ogg",music.AbsoluteUri+"?token=x",music.AbsoluteUri+"#frag","https://cdn.example/"+hashedSong})
        Check(!DesktopMusicUrlRules.TryValidate(value,local,out _));
});
Test("remote_music_rejects_other_origins_sibling_paths_and_encoded_traversal", () => {
    var root = DesktopRuntimeConfigRules.RemoteContentBase("https://cdn.example/racing/content/",false);
    Check(DesktopMusicUrlRules.TryValidate(new Uri(root,hashedSong).AbsoluteUri,root,out _));
    foreach(string value in new[]{"https://other.example/racing/content/"+hashedSong,"https://cdn.example/racing/content-other/"+hashedSong,"https://cdn.example/racing/content/%2e%2e/"+hashedSong,"http://cdn.example/racing/content/"+hashedSong})
        Check(!DesktopMusicUrlRules.TryValidate(value,root,out _));
});
Test("native_manifest_rejects_webgl_bundles_before_loading", () => {
    var entries = new List<P08BundleEntry>{new P08BundleEntry{id="actors",kind="actors",url="actors.bundle",asset="assets/actors.asset",sha256=new string('a',64),bytes=100}};
    for(int c=0;c<5;c++) {
        entries.Add(new P08BundleEntry{id="route-"+c,kind="route",courseIndex=c,url="route-"+c+".bundle",asset="assets/route"+c+".asset",sha256=new string('b',64),bytes=200});
        entries.Add(new P08BundleEntry{id="music-"+c,kind="music",url=hashedSong,sha256=new string('a',64),bytes=300});
    }
    var manifest = new P08ContentManifest {schema=1,contentHash="test-content",actorsId="actors",buildTarget="StandaloneWindows64",bundles=entries.ToArray()};
    Check(ContentManifestRules.Validate(manifest,"test-content",local,"StandaloneWindows64").Count==11);
    manifest.buildTarget="WebGL";
    try { ContentManifestRules.Validate(manifest,"test-content",local,"StandaloneWindows64"); }
    catch(InvalidDataException) { return; }
    throw new InvalidOperationException("Wrong platform accepted");
});
string source="Assets/RacingBois/Client/Application/DesktopRuntimeConfig.cs";
string[] sources={source,"Assets/RacingBois/Client/Application/ContentManifestRules.cs","src/Tests/RacingBois.DesktopConfig.Tests/Program.cs","src/Tests/RacingBois.DesktopConfig.Tests/RacingBois.DesktopConfig.Tests.csproj"};
string output=args.Length==2&&args[0]=="--report"?args[1]:"docs/p08/desktop/config-tests.json";
Directory.CreateDirectory(Path.GetDirectoryName(output));
File.WriteAllText(output,JsonSerializer.Serialize(new {generatedUtc=DateTimeOffset.UtcNow,passed=tests.Count-failed,failed,tests,source,sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(source))).ToLowerInvariant(),sources=Array.ConvertAll(sources,path=>new{path,sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()}),scope="Pure native installation/config/music URL acceptance. Does not establish Unity build, audio decode, rendering, live OCI connectivity, or Windows 10/11 machine acceptance."},new JsonSerializerOptions{WriteIndented=true}));
return failed==0?0:1;
