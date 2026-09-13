using System.Text.Json;
using System.Text.Json.Serialization;

namespace PawsPatchLauncher;

public sealed record SocialVersions(
    [property: JsonPropertyName("launcher")] string Launcher,
    [property: JsonPropertyName("mod")] string? Mod = null,
    [property: JsonPropertyName("channel")] string? Channel = null,
    [property: JsonPropertyName("content_id")] string? ContentId = null,
    [property: JsonPropertyName("patch")] string? Patch = null)
{
    public static SocialVersions? Read(JsonElement json)
    {
        if (json.ValueKind != JsonValueKind.Object || json.GetRawText().Length > 512) return null;
        string? Text(string key) => json.TryGetProperty(key,out var value) && value.ValueKind==JsonValueKind.String ? value.GetString() : null;
        var launcher=Text("launcher"); var mod=Text("mod"); var channel=Text("channel"); var content=Text("content_id"); var patch=Text("patch");
        if (!TryLauncher(launcher,out _) || mod is not (null or GameMod.Vanilla or GameMod.Immortals or GameMod.ArcaneWars)
            || channel is not (null or "stable" or "beta") || content is not null && (content.Length!=64 || !content.All(Uri.IsHexDigit))
            || patch is not null && (patch.Length>64 || patch.Any(c=>!char.IsAsciiLetterOrDigit(c) && c is not ('.' or '-' or '+')))) return null;
        return new(launcher!,mod,channel,content,patch);
    }

    public static bool TryLauncher(string? text,out Version version)
    {
        version=new Version(0,0,0,0);
        if (text is not { Length: >0 and <=32 } || !Version.TryParse(text,out var parsed)) return false;
        version=new Version(parsed.Major,parsed.Minor,Math.Max(0,parsed.Build),Math.Max(0,parsed.Revision));
        return true;
    }

    public static SocialVersions Installed(InstallState? state, ChannelManifest? installed, string launcher)
    {
        if (state?.AppliedSettings is not { } settings || installed is null || state.ReleaseId!=ChannelFingerprint.Create(installed)
            || settings.Channel!=installed.Channel) return new(launcher);
        return new(launcher,settings.Mod,settings.Channel,ModLibrary.ContentId(installed,settings.Mod),PawPatchVersions.Installed(state,installed));
    }
}

public enum PeerVersionStatus { Current, Unknown, Checking, Unavailable, OldLauncher, OldPatch, OldLauncherAndPatch }

public sealed record FriendVersionCatalog(string Launcher, string Channel, IReadOnlyDictionary<string,string> ContentIds,
    IReadOnlyDictionary<string,string?> PatchVersions, DateTimeOffset CheckedAt)
{
    public static FriendVersionCatalog Create(ChannelManifest channel,string launcher)
    {
        var ids=new Dictionary<string,string>();
        foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})
            try { ids[mod]=ModLibrary.ContentId(channel,mod); } catch(InvalidDataException) { }
        return new(launcher,channel.Channel,ids,ids.Keys.ToDictionary(mod=>mod,mod=>PawPatchVersions.ForChannel(channel,mod)),DateTimeOffset.UtcNow);
    }
}

public static class PeerVersionPolicy
{
    public static PeerVersionStatus Check(SocialPlayer player,FriendVersionCatalog? latest)
    {
        var versions=player.Versions;
        if (versions is null || !SocialVersions.TryLauncher(versions.Launcher,out var launcher)
            || !FriendConfiguration.TryParse(player.Configuration,player.Channel,out var settings)) return PeerVersionStatus.Unknown;
        if (latest is null || latest.Channel!=settings.Channel) return PeerVersionStatus.Checking;
        var oldLauncher=SocialVersions.TryLauncher(latest.Launcher,out var required) && launcher<required;
        if (versions.Mod!=settings.Mod || versions.Channel!=settings.Channel || versions.ContentId is not { Length:64 })
            return oldLauncher ? PeerVersionStatus.OldLauncher : PeerVersionStatus.Unknown;
        if (!latest.ContentIds.TryGetValue(settings.Mod,out var content)) return PeerVersionStatus.Unavailable;
        var oldPatch=!versions.ContentId.Equals(content,StringComparison.OrdinalIgnoreCase);
        if(GameMod.PawPatchSelected(settings))
        {
            if(!latest.PatchVersions.TryGetValue(settings.Mod,out var patch) || string.IsNullOrEmpty(patch))return PeerVersionStatus.Unavailable;
            if(string.IsNullOrEmpty(versions.Patch))return oldLauncher?PeerVersionStatus.OldLauncher:PeerVersionStatus.Unknown;
            oldPatch|=!string.Equals(versions.Patch,patch,StringComparison.OrdinalIgnoreCase);
        }
        return (oldLauncher,oldPatch) switch {
            (true,true)=>PeerVersionStatus.OldLauncherAndPatch, (true,false)=>PeerVersionStatus.OldLauncher,
            (false,true)=>PeerVersionStatus.OldPatch, _=>PeerVersionStatus.Current };
    }
}
