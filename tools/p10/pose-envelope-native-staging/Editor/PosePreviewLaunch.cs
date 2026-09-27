using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;

namespace RacingBois.Diagnostics.PoseEnvelopePreview.Editor
{
    /// <summary>Root-invoked owned-process launcher. No window/input automation, no process-name enumeration.</summary>
    public static class PosePreviewLaunch
    {
        [Serializable] private sealed class BuildRecord
        {public bool passed=false,sourceBindingPassed=false,editorStateRestored=false;public string sourceFingerprint="",output="";public PreviewFile[] playerFiles=Array.Empty<PreviewFile>();}
        [Serializable] private sealed class LaunchRecord
        {
            public string id,status,startedUtc,finishedUtc,buildRoot,captureRoot,sourceFingerprint,receipt,log,failureCode="";
            public int processId,exitCode;public bool timedOut,playerBytesStillMatch;public double maximumWallSeconds=130;
        }
        public static string Start(string buildDirectory,string captureDirectory,bool include20=true)
        {
            string build=Path.GetFullPath(buildDirectory),capture=Path.GetFullPath(captureDirectory);
            string boundary=Path.GetFullPath("Build/PoseEnvelopePreview")+Path.DirectorySeparatorChar;
            if(!build.StartsWith(boundary,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("unowned_build_root");
            PreviewBuildInputs.InsideProject(PreviewBuildInputs.Relative(build));PreviewBuildInputs.InsideProject(PreviewBuildInputs.Relative(capture));
            if(Directory.Exists(capture)||File.Exists(capture))throw new InvalidOperationException("capture_root_must_be_fresh");
            var bound=JsonUtility.FromJson<BuildRecord>(File.ReadAllText(Path.Combine(build,"PosePreview.build.json")));
            if(bound==null||!bound.passed||!bound.sourceBindingPassed||!bound.editorStateRestored||bound.playerFiles.Length==0)throw new InvalidOperationException("actual_verified_build_required");
            VerifyPlayer(build,bound.playerFiles);
            string id=Guid.NewGuid().ToString("N"),docs=Path.GetFullPath("docs/p10/pose-envelope-native-staging");Directory.CreateDirectory(docs);
            var record=new LaunchRecord{id=id,status="STARTING",startedUtc=DateTime.UtcNow.ToString("O"),buildRoot=build,captureRoot=capture,sourceFingerprint=bound.sourceFingerprint,
                receipt=Path.Combine(docs,"launch-"+id+".json"),log=Path.Combine(docs,"native-"+id+".log")};
            string arguments="--rb-pose-preview --rb-pose-output "+Quote(capture)+" --rb-pose-fingerprint "+Quote(bound.sourceFingerprint)+(include20?" --rb-pose-include20":"")+
                " -screen-fullscreen 0 -screen-width 1280 -screen-height 720 -logFile "+Quote(record.log);
            var process=new Process{StartInfo=new ProcessStartInfo{FileName=Path.Combine(build,"RacingBoisPosePreview.exe"),Arguments=arguments,WorkingDirectory=build,
                UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden}};
            if(!process.Start())throw new InvalidOperationException("owned_player_start_failed");record.processId=process.Id;record.status="STARTED";Write(record);
            // This worker owns the exact Process handle it started. A GPU hang cannot
            // keep an invisible diagnostic alive indefinitely or affect other players.
            Task.Run(()=>
            {
                try
                {
                    if(!process.WaitForExit(130000)){record.timedOut=true;record.status="TIMEOUT_KILLED";process.Kill();process.WaitForExit(5000);}
                    else record.status="EXITED";
                    if(process.HasExited)record.exitCode=process.ExitCode;
                    VerifyPlayer(build,bound.playerFiles);record.playerBytesStillMatch=true;
                }
                catch(Exception error){record.failureCode=error.GetType().Name;record.status="WATCHDOG_FAILED";}
                finally{record.finishedUtc=DateTime.UtcNow.ToString("O");Write(record);process.Dispose();}
            });
            return JsonUtility.ToJson(record,true);
        }
        private static void VerifyPlayer(string root,PreviewFile[] rows)
        {
            foreach(var row in rows)
            {
                if(string.IsNullOrEmpty(row.path)||Path.IsPathRooted(row.path)||row.path.Contains("\\")||row.path.Split('/').Any(p=>p==".."||p.Contains(":")))throw new InvalidDataException("player_manifest_path");
                string file=Path.GetFullPath(Path.Combine(root,row.path));
                if(!file.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||!File.Exists(file)||new FileInfo(file).Length!=row.bytes||PreviewBuildInputs.Digest(file)!=row.sha256)
                    throw new InvalidDataException("player_bytes_changed");
            }
        }
        private static string Quote(string value)
        {
            var text=new StringBuilder("\"");int slash=0;
            foreach(char c in value)
            {
                if(c=='\\'){slash++;continue;}
                if(c=='\"'){text.Append('\\',slash*2+1);text.Append(c);slash=0;continue;}
                text.Append('\\',slash);slash=0;text.Append(c);
            }
            text.Append('\\',slash*2);text.Append('"');return text.ToString();
        }
        private static void Write(LaunchRecord record)=>File.WriteAllText(record.receipt,JsonUtility.ToJson(record,true));
    }
}
