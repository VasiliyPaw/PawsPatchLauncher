using System.Net.Http;

namespace PawsPatchLauncher;

public sealed partial class AccountService
{
    internal ServiceConnection Connection { get; } = new();

    internal async Task ProbeConnectionAsync(CancellationToken ct)
    {
        var observation = Connection.Begin();
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
            timeout.CancelAfter(TimeSpan.FromSeconds(4));
            using var request = new HttpRequestMessage(HttpMethod.Get, ProjectUrl + "/auth/v1/health");
            request.Headers.Add("apikey", PublishableKey);
            using var response = await _http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token).ConfigureAwait(false);
            Connection.Complete(observation, (int)response.StatusCode < 500);
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested) { }
        catch (Exception error) when (error is HttpRequestException or OperationCanceledException)
        { Connection.Complete(observation, false); }
    }
}
