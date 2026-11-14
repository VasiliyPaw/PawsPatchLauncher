using System.Net.Http;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed partial class AccountService
{
    public async Task<IReadOnlyList<RebornBuild>> GetRebornHistoryAsync(CancellationToken ct = default)
    {
        IReadOnlyList<RebornBuild> history = [];
        await WithAccountAsync(async () =>
        {
            if (!PawsTeam && AdminLevel < 1) throw new AccountException("reborn_access_denied");
            using var result = await ReadRebornCatalogAsync("history",ct).ConfigureAwait(false);
            history = ReadRebornResponse<IReadOnlyList<RebornBuild>>(() =>
            {
                var rows = result.RootElement.GetProperty("releases");
                if (rows.GetArrayLength() > RebornHistory.Limit) throw new AccountException("invalid_response");
                var parsed = rows.EnumerateArray().Select(RebornBuild.Read).ToArray();
                if (parsed.Select(b => b.Id).Distinct().Count() != parsed.Length) throw new AccountException("invalid_response");
                return parsed;
            });
        },ct).ConfigureAwait(false);
        return history;
    }

    public async Task<IReadOnlyList<RebornBuild>> GetRebornBuildsAsync(CancellationToken ct = default)
    {
        IReadOnlyList<RebornBuild> builds = [];
        await WithAccountAsync(async () =>
        {
            if (!PawsTeam && AdminLevel < 1) throw new AccountException("reborn_access_denied");
            using var result = await ReadRebornCatalogAsync("catalog",ct).ConfigureAwait(false);
            builds = ReadRebornResponse<IReadOnlyList<RebornBuild>>(() =>
            {
                var rows = result.RootElement.GetProperty("releases");
                if (rows.GetArrayLength() > 2) throw new AccountException("invalid_response");
                var parsed = rows.EnumerateArray().Select(RebornBuild.Read).ToArray();
                if (parsed.Select(b => b.Channel).Distinct().Count() != parsed.Length) throw new AccountException("invalid_response");
                return parsed;
            });
        },ct).ConfigureAwait(false);
        return builds;
    }

    private async Task<JsonDocument> ReadRebornCatalogAsync(string action,CancellationToken ct)
    {
        try { return await RequestAsync(HttpMethod.Post,"reborn-builds?action="+action,null,_session!.AccessToken,ct,portal:true).ConfigureAwait(false); }
        // These channels intentionally ship empty before the first accepted build/backend activation.
        // Only the gateway's explicit missing-function response is empty; auth/network failures remain errors.
        catch(AccountException error) when(error.Code=="reborn_not_deployed") { return JsonDocument.Parse("{\"releases\":[]}"); }
    }
    public async Task<RebornTicket> GetRebornTicketAsync(RebornBuild selected, CancellationToken ct = default)
    {
        RebornBuild.Validate(selected); RebornTicket? ticket = null;
        await WithAccountAsync(async () =>
        {
            if (!PawsTeam && AdminLevel < 1) throw new AccountException("reborn_access_denied");
            using var result = await RequestAsync(HttpMethod.Post,$"reborn-builds?action=download&channel={selected.Channel}&build_id={selected.Id}",null,_session!.AccessToken,ct,portal:true).ConfigureAwait(false);
            ticket = ReadRebornResponse(() =>
            {
            var data = result.RootElement; var build = RebornBuild.Read(data.GetProperty("release"));
            if (!Uri.TryCreate(data.GetProperty("url").GetString(),UriKind.Absolute,out var url) || !data.GetProperty("expires_at").TryGetDateTimeOffset(out var expires)) throw new AccountException("invalid_response");
            var storage = new Uri(ProjectUrl);
            if (build.Id != selected.Id || build.Channel != selected.Channel || build.Version != selected.Version || build.Sha256 != selected.Sha256 || build.Size != selected.Size
                || build.Executable != selected.Executable || url.Scheme != "https" || url.Host != storage.Host || url.Port != storage.Port || url.UserInfo.Length > 0 || url.Fragment.Length > 0
                || url.AbsolutePath != $"/storage/v1/object/sign/paw-reborn-builds/{build.Channel}/{build.Id}.zip" || string.IsNullOrEmpty(url.Query)
                || expires <= _clock() || expires > _clock().AddMinutes(3)) throw new AccountException("invalid_response");
            return new RebornTicket(build,url,expires);
            });
        },ct).ConfigureAwait(false);
        return ticket!;
    }
    private static T ReadRebornResponse<T>(Func<T> read)
    {
        try { return read(); }
        catch (Exception error) when (error is InvalidDataException or KeyNotFoundException or InvalidOperationException or FormatException or JsonException or ArgumentException)
        { throw new AccountException("invalid_response"); }
    }
}
