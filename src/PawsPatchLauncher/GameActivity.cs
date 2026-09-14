using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace PawsPatchLauncher;

public sealed record GameParticipant(
    [property: JsonPropertyName("key")] string Key,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("bot")] bool Bot,
    [property: JsonPropertyName("profile")] GameParticipantProfile? Profile = null,
    [property: JsonPropertyName("team")] int? Team = null,
    [property: JsonPropertyName("color")] string? Color = null,
    [property: JsonPropertyName("race"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Race = null,
    [property: JsonPropertyName("subrace"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Subrace = null);

public sealed record GameParticipantProfile(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("nickname")] string Nickname,
    [property: JsonPropertyName("display_name")] string DisplayName,
    [property: JsonPropertyName("avatar_revision")] DateTimeOffset? AvatarRevision = null);

public sealed record GameActivity(
    [property: JsonPropertyName("phase")] string Phase,
    [property: JsonPropertyName("multiplayer")] bool Multiplayer = false,
    [property: JsonPropertyName("elapsed")] int? ElapsedSeconds = null,
    [property: JsonPropertyName("width")] int? Width = null,
    [property: JsonPropertyName("height")] int? Height = null,
    [property: JsonPropertyName("room")] string? Room = null,
    [property: JsonPropertyName("self")] string? Self = null,
    [property: JsonPropertyName("players")] IReadOnlyList<GameParticipant>? Players = null)
{
    public const int MaximumBytes = 16384;
    public static bool ValidPhase(string? phase) => phase is "menu" or "lobby" or "match" or "loading" or "editor";
    public static GameActivity? Read(JsonElement value, bool details = false)
    {
        if (value.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined) return null;
        try
        {
            if (value.ValueKind != JsonValueKind.Object || Encoding.UTF8.GetByteCount(value.GetRawText()) > (details ? MaximumBytes * 2 : MaximumBytes)) return null;
            var result = value.Deserialize<GameActivity>();
            if (result is null || !ValidPhase(result.Phase) || result.ElapsedSeconds is < 0 or > 604800
                || (result.Width is not null || result.Height is not null) && (result.Width is not (>= 16 and <= 8192) || result.Height is not (>= 16 and <= 8192))
                || result.Room is not null && (result.Room.Length != 64 || !result.Room.All(Uri.IsHexDigit))
                || result.Self is not null && !ValidKey(result.Self)) return null;
            var players = result.Players ?? [];
            if (players.Count > 64 || players.Any(p => p is null) || players.Select(p => p.Key).Distinct().Count() != players.Count) return null;
            foreach (var player in players)
            {
                if (!ValidKey(player.Key) || string.IsNullOrWhiteSpace(player.Name) || player.Name.Length > 80 || player.Name.Any(char.IsControl)) return null;
                if (player.Team is < 1 or > 64 || player.Color is not null && !ValidColor(player.Color)) return null;
                if (player.Race is not null && !ValidFactionId(player.Race) || player.Subrace is not null && !ValidFactionId(player.Subrace)) return null;
                if (player.Profile is { } profile)
                {
                    if (!details || player.Bot || profile.Id == Guid.Empty || string.IsNullOrWhiteSpace(profile.Nickname) || string.IsNullOrWhiteSpace(profile.DisplayName)) return null;
                    AccountService.ValidateNickname(profile.Nickname); AccountService.ValidateDisplayName(profile.DisplayName);
                }
            }
            if (result.Self is not null && !players.Any(p => p.Key == result.Self && !p.Bot)) return null;
            if (!result.Multiplayer && result.Room is not null) return null;
            if (result.Phase is not ("lobby" or "match") && (players.Count != 0 || result.Room is not null || result.Self is not null)) return null;
            return result;
        }
        catch (Exception error) when (error is JsonException or InvalidOperationException or AccountException or ArgumentException) { return null; }
    }
    public static bool ValidKey(string? value) => value is { Length: > 0 and <= 32 } && value.All(c => char.IsAsciiLetterOrDigit(c) || c is '-' or '_');
    public static bool ValidColor(string? value) => value is { Length: 7 } && value[0] == '#' && value.AsSpan(1).ToString().All(Uri.IsHexDigit);
    public static bool ValidFactionId(string? value) => value is { Length: > 0 and <= 80 } && value.All(c => char.IsAsciiLetterOrDigit(c) || c is '-' or '_');
    public GameActivity Summary() => this with { Room = null, Self = null, Players = null };
}

public sealed record GameActivityDetails(GameActivity Activity, DateTimeOffset ObservedAt);
