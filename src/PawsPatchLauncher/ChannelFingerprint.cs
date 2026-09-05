using System.Security.Cryptography;
using System.Text;

namespace PawsPatchLauncher;

public static class ChannelFingerprint
{
    public static string Create(ChannelManifest channel)
    {
        var builder = new StringBuilder();
        builder.Append(channel.Channel.ToLowerInvariant()).Append('\n');
        builder.Append(channel.Game.Version).Append('|').Append(channel.Game.SteamBuild).Append('\n');
        foreach (var hash in channel.Game.K2ExeSha256.OrderBy(value => value, StringComparer.OrdinalIgnoreCase))
            builder.Append(hash.ToUpperInvariant()).Append('\n');
        foreach (var package in channel.Packages.OrderBy(package => package.Id, StringComparer.OrdinalIgnoreCase))
        {
            builder.Append(package.Id.ToLowerInvariant()).Append('|')
                .Append(package.Version).Append('|')
                .Append(package.Priority).Append('|')
                .Append(package.Size).Append('|')
                .Append(package.Sha256.ToUpperInvariant()).Append('\n');
        }
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(builder.ToString())));
    }
}
