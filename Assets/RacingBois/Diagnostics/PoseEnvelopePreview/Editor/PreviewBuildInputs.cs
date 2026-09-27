using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Diagnostics.PoseEnvelopePreview.Editor
{
    [Serializable] public sealed class PreviewFile{public string path,sha256;public long bytes;}
    [Serializable] public sealed class PreviewSelection
    {public int schema;public PreviewFile bike,rider,pipeline,fixture;public PreviewFile[] inputs;public string scope;}
    internal static class PreviewBuildInputs
    {
        [Serializable] private sealed class Proof{public int schema=0;public bool passed=false;public AssemblyProof[] assemblies=Array.Empty<AssemblyProof>();}
        [Serializable] private sealed class AssemblyProof{public string name="",path="",sha256="",pdbSha256="",mvid="";public bool passed=false,pdbMatchesAssembly=false;public Document[] documents=Array.Empty<Document>();}
        [Serializable] private sealed class Document{public string path="",sha256="";public bool matches=false;}
        internal static readonly string[] AssemblyNames={"RacingBois.Diagnostics.PoseEnvelopePreview","RacingBois.Diagnostics.PoseEnvelopePreview.Editor","RacingBois.Client.Presentation","RacingBois.Gameplay.Definitions","RacingBois.Golden"};
        internal static string InsideProject(string relative)
        {
            if(string.IsNullOrEmpty(relative)||Path.IsPathRooted(relative)||relative.Contains("\\")||relative.Split('/').Any(p=>p==""||p=="."||p==".."||p.Contains(":")))throw new InvalidDataException("noncanonical_project_path");
            string root=Path.GetFullPath("."),path=Path.GetFullPath(relative);
            if(!path.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("project_path_escape");
            for(string p=path;p!=null&&!string.Equals(p,root,StringComparison.OrdinalIgnoreCase);p=Path.GetDirectoryName(p))
                if((File.Exists(p)||Directory.Exists(p))&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException("source_reparse_point");
            return path;
        }
        internal static string Digest(string path)
        {using(var sha=SHA256.Create())using(var stream=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
        internal static PreviewFile Row(string path)=>new PreviewFile{path=Relative(path),sha256=Digest(path),bytes=new FileInfo(path).Length};
        internal static string Relative(string path)=>Path.GetRelativePath(Path.GetFullPath("."),Path.GetFullPath(path)).Replace('\\','/');
        internal static void Verify(PreviewFile row)
        {if(row==null||!File.Exists(InsideProject(row.path))||Digest(row.path)!=row.sha256||new FileInfo(row.path).Length!=row.bytes)throw new InvalidDataException("bound_input_changed");}
        internal static string Fingerprint(IEnumerable<PreviewFile> rows)
        {using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n",rows.Select(r=>r.path+" "+r.sha256))))).Replace("-","").ToLowerInvariant();}
        internal static PreviewSelection Selection(string path)
        {
            InsideProject(path);var result=JsonUtility.FromJson<PreviewSelection>(File.ReadAllText(path));
            if(result==null||result.schema!=1||result.inputs==null||result.inputs.Length<5)throw new InvalidDataException("selection_not_bound");
            foreach(var row in result.inputs.Concat(new[]{result.bike,result.rider,result.pipeline,result.fixture}))Verify(row);
            return result;
        }
        internal static void VerifyExecutingAssemblies(string path)
        {
            InsideProject(path);var proof=JsonUtility.FromJson<Proof>(File.ReadAllText(path));
            if(proof==null||proof.schema!=1||!proof.passed||proof.assemblies==null)throw new InvalidDataException("compiled_proof_required");
            foreach(string name in AssemblyNames)
            {
                var record=proof.assemblies.SingleOrDefault(p=>p.name==name);var assembly=AppDomain.CurrentDomain.GetAssemblies().SingleOrDefault(a=>a.GetName().Name==name);
                if(record==null||assembly==null||!record.passed||!record.pdbMatchesAssembly||assembly.ManifestModule.ModuleVersionId.ToString()!=record.mvid)throw new InvalidDataException("loaded_assembly_not_attested");
                InsideProject(record.path);if(Digest(record.path)!=record.sha256||Digest(Path.ChangeExtension(record.path,".pdb"))!=record.pdbSha256)throw new InvalidDataException("compiled_binary_changed");
                foreach(var document in record.documents)
                {
                    if(string.IsNullOrEmpty(document.sha256))
                    {if(!document.path.StartsWith("Library/Bee/artifacts/",StringComparison.Ordinal)||!document.path.EndsWith("/Unity.SourceGenerators/Unity.MonoScriptGenerator.MonoScriptInfoGenerator/AssemblyMonoScriptTypes.generated.cs",StringComparison.Ordinal))throw new InvalidDataException("unbound_source_document");continue;}
                    InsideProject(document.path);if(!document.matches||Digest(document.path)!=document.sha256)throw new InvalidDataException("compiled_source_changed");
                }
            }
        }
        internal static PreviewFile[] Snapshot(string scene,string selectionPath,string proofPath,PreviewSelection selection,string buildPipelinePath)
        {
            var files=new HashSet<string>(StringComparer.Ordinal);
            foreach(string folder in new[]{"Assets/RacingBois/Client","Packages/com.racingbois.foundation/Runtime",PosePreviewBuilder.AssetRoot})
                foreach(string file in Directory.GetFiles(folder,"*",SearchOption.AllDirectories))
                    if(new[]{".cs",".asmdef"}.Contains(Path.GetExtension(file)))Add(files,file);
            foreach(string logical in AssetDatabase.GetDependencies(new[]{scene,selection.bike.path,selection.rider.path,selection.pipeline.path,buildPipelinePath},true))
            {
                if(logical=="Resources/unity_builtin_extra"||logical=="Library/unity default resources")continue;
                string physical=logical;
                if(logical.StartsWith("Packages/",StringComparison.Ordinal))
                {
                    var package=UnityEditor.PackageManager.PackageInfo.FindForAssetPath(logical);string name=logical.Split('/')[1];
                    if(package==null||package.name!=name)throw new InvalidDataException("virtual_package_unresolved");
                    string relative=Relative(package.resolvedPath),prefix="Library/PackageCache/"+name+"@";
                    if(relative!="Packages/"+name&&!(relative.StartsWith(prefix,StringComparison.Ordinal)&&relative.Length>prefix.Length&&!relative.Substring(prefix.Length).Contains("/")))throw new InvalidDataException("package_root_not_bounded");
                    Add(files,Path.Combine(package.resolvedPath,"package.json"));physical=Path.Combine(package.resolvedPath,logical.Substring(("Packages/"+name+"/").Length));
                }
                Add(files,physical);
            }
            foreach(var input in selection.inputs)Add(files,input.path);
            foreach(string path in new[]{selectionPath,proofPath,scene,"Packages/manifest.json","Packages/packages-lock.json","ProjectSettings/ProjectSettings.asset","ProjectSettings/GraphicsSettings.asset","ProjectSettings/QualitySettings.asset"})Add(files,path);
            return files.OrderBy(p=>p,StringComparer.Ordinal).Select(Row).ToArray();
        }
        private static void Add(HashSet<string> files,string path)
        {
            string relative=Relative(path);InsideProject(relative);if(!File.Exists(relative))throw new FileNotFoundException("dependency_file_missing",relative);
            files.Add(relative);if(File.Exists(relative+".meta")){InsideProject(relative+".meta");files.Add(relative+".meta");}
        }
    }
}
