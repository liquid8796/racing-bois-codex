namespace RacingBois.Server.Host.Multiplayer;

internal static class RealmPathPolicy
{
    public static string ResolvePrivateDataRoot(string directory, string webRoot)
    {
        string data = Path.TrimEndingDirectorySeparator(Path.GetFullPath(directory));
        string web = Path.TrimEndingDirectorySeparator(Path.GetFullPath(webRoot));
        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        string prefix = Path.EndsInDirectorySeparator(web) ? web : web + Path.DirectorySeparatorChar;
        if (data.Equals(web, comparison) || data.StartsWith(prefix, comparison))
            throw new InvalidOperationException("DataRoot must be outside the public WebRoot.");
        return data;
    }
}
