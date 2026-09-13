using System.Text;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public static class GameMenuMetadata
{
    public const string FileName = "paws_launch_versions.ini";

    public static string Create(ChannelManifest channel, UserSettings settings)
    {
        GameMod.Validate(settings);
        string Value(string? value)
        {
            if (value is null || !Regex.IsMatch(value, @"\A[0-9A-Za-z.+_ -]{1,64}\z"))
                throw new InvalidDataException("Invalid menu version metadata.");
            return value;
        }
        var text = new StringBuilder("[Versions]\nMod=").Append(settings.Mod).Append('\n');
        if (settings.Mod != GameMod.Vanilla)
            text.Append("ModVersion=").Append(Value(channel.ModGuides.FirstOrDefault(g => g.Id == settings.Mod)?.Version
                ?? channel.Packages.FirstOrDefault(p => p.Id == settings.Mod)?.Version)).Append('\n');
        if (GameMod.PawPatchSelected(settings))
        {
            var version = PawPatchVersions.ForChannel(channel, settings.Mod);
            text.Append("PawPatch=").Append(Value(version)).Append('\n');
            if (settings.Channel is not ("stable" or "beta")) throw new InvalidDataException("Unknown patch channel.");
            text.Append("PatchChannel=").Append(settings.Channel).Append('\n');
        }
        return text.ToString();
    }

    public static async Task WriteAsync(string root, ChannelManifest channel, UserSettings settings)
    {
        var path = CryptoAndIO.SafeChildPath(root, FileName);
        RemovalSafety.CheckNoLinks(path);
        await CryptoAndIO.AtomicWriteTextAsync(path, Create(channel, settings));
    }
}
