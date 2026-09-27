using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;

namespace RacingBois.Golden
{
    /// <summary>Opt-in captures from the actual standalone review player. It never runs in a gameplay scene.</summary>
    [DisallowMultipleComponent]
    public sealed class GoldenCaptureRunner : MonoBehaviour
    {
        [Serializable] public sealed class Capture
        {
            public string subject, file, sha256;
            public int view, lod, width, height;
            public long bytes;
        }
        [Serializable] public sealed class Receipt
        {
            public string startedUtc, finishedUtc, unityVersion, graphicsDevice, graphicsApi, operatingSystem, failure;
            public bool completed;
            public int width, height;
            public Capture[] captures;
            public string scope = "Actual standalone inspection-scene captures. No gameplay, concept-fidelity or performance acceptance is inferred.";
        }

        private IEnumerator Start()
        {
#if UNITY_EDITOR
            yield break;
#else
            string output = null;
            var args = Environment.GetCommandLineArgs();
            for (int i = 1; i < args.Length - 1; i++)
                if (args[i] == "--rb-review-output") { output = args[i + 1]; break; }
            if (output == null) yield break;
            var controller = GetComponent<GoldenReviewController>();
            if (controller == null || !Path.IsPathRooted(output) || Directory.Exists(output) || File.Exists(output))
            { Debug.LogError("Review capture requires its review controller and a new absolute output directory."); Application.Quit(2); yield break; }
            output = Path.GetFullPath(output);
            Directory.CreateDirectory(output);
            Application.runInBackground = true;
            var receipt = new Receipt
            {
                startedUtc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture), unityVersion = Application.unityVersion,
                graphicsDevice = SystemInfo.graphicsDeviceName, graphicsApi = SystemInfo.graphicsDeviceType.ToString(),
                operatingSystem = SystemInfo.operatingSystem
            };
            var captures = new List<Capture>();
            controller.ShowControls = false; controller.SetTurntable(false);
            // Real startup and shader warm-up frames precede the first capture.
            yield return new WaitForSecondsRealtime(3f);
            for (int subject = 0; subject < controller.Subjects.Length; subject++)
            {
                controller.SetSubject(subject);
                for (int lod = 0; lod < 3; lod++)
                {
                    controller.SetLod(lod);
                    int firstView = controller.Subjects[subject].IsEnvironment ? 4 : 0;
                    int lastView = controller.Subjects[subject].IsEnvironment ? 4 : 5;
                    for (int view = firstView; view <= lastView; view++)
                    {
                        controller.SetView(view);
                        yield return new WaitForSecondsRealtime(.5f);
                        yield return new WaitForEndOfFrame();
                        Texture2D screenshot = null;
                        try
                        {
                            screenshot = ScreenCapture.CaptureScreenshotAsTexture();
                            if (screenshot == null || screenshot.width < 640 || screenshot.height < 360)
                                throw new InvalidOperationException("Missing or undersized rendered frame.");
                            string file = "subject-" + subject + "-lod-" + lod + "-view-" + view + ".png";
                            byte[] bytes = screenshot.EncodeToPNG();
                            if (bytes == null || bytes.Length < 1000) throw new InvalidOperationException("Invalid PNG capture.");
                            using (var stream = new FileStream(Path.Combine(output, file), FileMode.CreateNew, FileAccess.Write)) stream.Write(bytes, 0, bytes.Length);
                            string digest;
                            using (var hash = SHA256.Create()) digest = BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
                            captures.Add(new Capture { subject = controller.Subjects[subject].Id, file = file, sha256 = digest,
                                view = view, lod = lod, width = screenshot.width, height = screenshot.height, bytes = bytes.Length });
                        }
                        catch (Exception error) { receipt.failure = error.GetType().Name + ": " + error.Message; }
                        finally { if (screenshot != null) Destroy(screenshot); }
                        if (!string.IsNullOrEmpty(receipt.failure)) break;
                    }
                    if (!string.IsNullOrEmpty(receipt.failure)) break;
                }
                if (!string.IsNullOrEmpty(receipt.failure)) break;
            }
            receipt.width = Screen.width; receipt.height = Screen.height;
            receipt.finishedUtc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture);
            receipt.captures = captures.ToArray(); receipt.completed = string.IsNullOrEmpty(receipt.failure) && captures.Count > 0;
            File.WriteAllText(Path.Combine(output, "capture-receipt.json"), JsonUtility.ToJson(receipt, true));
            Application.Quit(receipt.completed ? 0 : 2);
#endif
        }
    }
}
