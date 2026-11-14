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
        try { return await RequestAsync(HttpMethod.Post,"reborn-builds?action="+action+"&protocol=2",null,_session!.AccessToken,ct,portal:true).ConfigureAwait(false); }
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
            using var result = await RequestAsync(HttpMethod.Post,$"reborn-builds?action=download&protocol=2&channel={selected.Channel}&build_id={selected.Id}",null,_session!.AccessToken,ct,portal:true).ConfigureAwait(false);
            ticket = ReadRebornResponse(() =>
            {
            var data = result.RootElement; var build = RebornBuild.Read(data.GetProperty("release"));
            if (!Uri.TryCreate(data.GetProperty("url").GetString(),UriKind.Absolute,out var url) || !data.GetProperty("expires_at").TryGetDateTimeOffset(out var expires)) throw new AccountException("invalid_response");
            if (!RebornDownloadPolicy.SameBuild(build,selected)) throw new AccountException("invalid_response");
            DateTimeOffset? upstreamExpiry = null;
            if (build.DownloadProvider == "github")
            {
                if (data.GetProperty("ticket_version").GetInt32() != 2) throw new AccountException("invalid_response");
                upstreamExpiry = data.GetProperty("url_expires_at").GetDateTimeOffset();
            }
            var parsed = new RebornTicket(build,url,expires,upstreamExpiry);
            RebornDownloadPolicy.Validate(parsed,new Uri(ProjectUrl),_clock());
            return parsed;
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
