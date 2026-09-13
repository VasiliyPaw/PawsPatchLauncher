using System.Net;
using System.Net.Http;
using PawsPatchLauncher;

internal static class ConnectionTests
{
    private sealed class Handler : HttpMessageHandler
    {
        internal Func<CancellationToken, Task<HttpResponseMessage>> Reply = _ => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("true") });
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) => Reply(cancellationToken);
    }
    internal static async Task<int> RunAsync(string root)
    {
        var n = 0; void Check(bool ok, string why) { n++; if (!ok) throw new Exception("Connectivity: " + why); }
        var status = new ServiceConnection(); int changes = 0; status.Changed += () => changes++;
        Check(status.Available is null, "initial unknown state falsely reports failure");
        var old = status.Begin(); var fresh = status.Begin();
        status.Complete(fresh, true); status.Complete(old, false);
        Check(status.Available == true && changes == 1, "old timeout overrides newer success");
        status.Complete(status.Begin(), true); Check(changes == 1, "every successful poll redraws banner");
        status.Complete(status.Begin(), false); Check(status.Available == false && changes == 2, "disconnect event missing");
        var handler = new Handler();
        using var account = new AccountService(new AccountSessionStore(Path.Combine(root, "connection")), handler);
        Check(await account.IsNicknameAvailableAsync("tester"), "success fixture invalid");
        Check(account.Connection.Available == true, "normal response does not establish connection");
        handler.Reply = _ => throw new HttpRequestException("fixture");
        try { await account.IsNicknameAvailableAsync("tester"); throw new Exception("Expected failure"); } catch (AccountException e) when (e.Code == "network") { }
        Check(account.Connection.Available == false, "transport failure does not block account UI");
        handler.Reply = _ => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("true") });
        await account.ProbeConnectionAsync(CancellationToken.None);
        Check(account.Connection.Available == true, "health probe cannot recover a disconnected client");
        handler.Reply = _ => Task.FromResult(new HttpResponseMessage(HttpStatusCode.ServiceUnavailable) { Content = new StringContent("{}") });
        await account.ProbeConnectionAsync(CancellationToken.None); Check(account.Connection.Available == false, "server outage treated as connected");
        handler.Reply = _ => Task.FromResult(new HttpResponseMessage(HttpStatusCode.BadRequest) { Content = new StringContent("{\"error_code\":\"invalid_credentials\"}") });
        try { await account.IsNicknameAvailableAsync("tester"); throw new Exception("Expected rejection"); } catch (AccountException e) when (e.Code == "invalid_credentials") { }
        Check(account.Connection.Available == true, "wrong credentials are reported as no internet");
        using var cancel = new CancellationTokenSource();
        handler.Reply = async token => { cancel.Cancel(); await Task.Delay(100, token); return new HttpResponseMessage(HttpStatusCode.OK); };
        try { await account.IsNicknameAvailableAsync("tester", cancel.Token); throw new Exception("Expected cancellation"); } catch (OperationCanceledException) { }
        Check(account.Connection.Available == true, "canceled view read creates a false offline banner");
        using var cancelProbe = new CancellationTokenSource(); cancelProbe.Cancel();
        await account.ProbeConnectionAsync(cancelProbe.Token);
        Check(account.Connection.Available == true, "shutdown cancellation changes network status");
        Console.WriteLine($"CONNECTION STATUS / TRANSPORT PASS {n}: ordered results, quiet polls, failures, recovery, HTTP errors, view/shutdown cancellation; mocked network");
        return n;
    }
}
