namespace PawsPatchLauncher;

public static class RemovalSafety
{
    public static void CheckNoLinks(string path)
    {
        for (var current = Path.GetFullPath(path); current is not null; current = Path.GetDirectoryName(current))
        {
            if ((File.Exists(current) || Directory.Exists(current)) && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Symbolic links/junctions are not allowed during uninstall: " + current);
        }
    }
}
