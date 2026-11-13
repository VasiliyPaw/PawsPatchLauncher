namespace PawsPatchLauncher;

public sealed record MissingGameExecutable(string Directory, string Path, bool IsPatchHelper)
{
    public string FileName => System.IO.Path.GetFileName(Path);

    public static MissingGameExecutable? Find(string? directory, string? selectedExecutable = null, InstallState? installed = null)
    {
        if (string.IsNullOrWhiteSpace(directory)) return null;
        try
        {
            var root = System.IO.Path.GetFullPath(directory.Trim().Trim('"'));
            if (!System.IO.Directory.Exists(root)) return null;
            var vanilla = System.IO.Path.Combine(root, "k2.exe");
            // Distinguish a recognizable installation from an arbitrary folder.
            if (!File.Exists(vanilla))
                return File.Exists(System.IO.Path.Combine(root, "Data.rwd")) || File.Exists(System.IO.Path.Combine(root, ".pawpatch/state.json"))
                    ? new(root, vanilla, false) : null;
            var name = System.IO.Path.GetFileName(selectedExecutable);
            if (string.IsNullOrEmpty(name) || name.Equals("k2.exe", StringComparison.OrdinalIgnoreCase)
                || !name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase)) return null;
            var expected = installed?.Modules.Values.Where(m => m.Enabled).SelectMany(m => m.Files)
                .Any(f => f.Path.Replace('\\', '/').Equals(name, StringComparison.OrdinalIgnoreCase)) == true;
            var helper = System.IO.Path.Combine(root, name);
            return expected && !File.Exists(helper) ? new(root, helper, true) : null;
        }
        catch (Exception error) when (error is ArgumentException or IOException or UnauthorizedAccessException or NotSupportedException) { return null; }
    }
}
