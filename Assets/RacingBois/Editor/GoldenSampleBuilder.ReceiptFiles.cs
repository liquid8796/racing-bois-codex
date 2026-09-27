using System;
using System.IO;
using System.Text;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Publish a complete sibling file; never truncate a receipt held by a mapped reader.</summary>
    internal static class GoldenReceiptFiles
    {
        internal static bool ImportSucceeded(bool passed, bool sourceBindingPassed, string failure)
            => passed && sourceBindingPassed && string.IsNullOrEmpty(failure);

        internal static void WriteAtomic(string path, string json)
        {
            if (string.IsNullOrEmpty(path)) throw new ArgumentException("Receipt path required.", nameof(path));
            if (json == null) throw new ArgumentNullException(nameof(json));
            string destination = Path.GetFullPath(path);
            string directory = Path.GetDirectoryName(destination);
            Directory.CreateDirectory(directory);
            string temporary = Path.Combine(directory, "." + Path.GetFileName(destination) + "." + Guid.NewGuid().ToString("N") + ".tmp");
            try
            {
                using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    byte[] bytes = new UTF8Encoding(false).GetBytes(json);
                    stream.Write(bytes, 0, bytes.Length); stream.Flush(true);
                }
                if (File.Exists(destination)) File.Replace(temporary, destination, null);
                else File.Move(temporary, destination);
            }
            finally
            {
                // Delete only the unique temporary file created by this call. A rejected
                // replace leaves the previous receipt intact; it never falls back to truncation.
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }
    }
}
