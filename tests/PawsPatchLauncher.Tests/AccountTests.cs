using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class AccountTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var checks = 0;
        void Check(bool ok, string reason) { checks++; if (!ok) throw new Exception("Account: " + reason); }
        async Task Error(Func<Task> action, string code)
        {
            try { await action(); throw new Exception("Expected account failure: " + code); }
            catch (AccountException error) { Check(error.Code == code, "error " + error.Code + " instead of " + code); Check(!error.ToString().Contains("fixture-secret"), "error leaked credential"); }
        }
        var now = DateTimeOffset.UtcNow;
        var user = Guid.NewGuid().ToString();
        string User() => JsonSerializer.Serialize(new { id = user, email = "player@example.invalid", user_metadata = new { nickname = "NotTheRealNickname" } });
        string Session(string access = "fixture-access", string refresh = "fixture-refresh") => "{\"access_token\":\"" + access + "\",\"refresh_token\":\"" + refresh + "\",\"expires_in\":3600,\"user\":" + User() + "}";
        string Profile() => JsonSerializer.Serialize(new[] { new { id = user, nickname = "FixturePaw" } });
        AccountSessionStore Vault(string name) => new(Path.Combine(root, "accounts", name));
        var store = Vault("persist");
        var handler = new FakeAuth(async request =>
        {
            Check(request.RequestUri!.Host == "trdzsdclscuwwmxnepyt.supabase.co", "credentials sent to wrong origin");
            Check(request.Headers.GetValues("apikey").Single() == AccountService.PublishableKey, "wrong public key");
            if (request.RequestUri.PathAndQuery.Contains("grant_type=password"))
            {
                var content = await request.Content!.ReadAsStringAsync();
                Check(content.Contains("fixture-secret-password"), "password not sent to Auth");
                Check(request.Headers.Authorization is null, "stale access token attached to password login");
                return Ok(Session());
            }
            if (request.RequestUri.AbsolutePath.EndsWith("/user")) return Ok(User());
            if (request.RequestUri.AbsolutePath.EndsWith("paw_profiles")) return Ok(Profile());
            throw new Exception("Unexpected auth request");
        });
        using (var service = new AccountService(store, handler))
        {
            await service.RestoreAsync(); Check(service.State == AccountState.Guest && handler.Calls == 0, "guest made a request");
            await service.SignInAsync("player@example.invalid", "fixture-secret-password");
            Check(service.State == AccountState.SignedIn && service.Nickname == "fixturepaw", "login/profile incorrect or trusted mutable metadata");
            Check(service.DisplayName == "FixturePaw", "legacy display name capitalization lost");
            Check(service.Email == "player@example.invalid", "email not restored");
            var protectedBytes = await File.ReadAllBytesAsync(store.SessionPath);
            var text = Encoding.UTF8.GetString(protectedBytes);
            Check(!text.Contains("fixture") && !text.Contains("player@"), "session persisted as plaintext");
            Check(!store.Read()!.ToString().Contains("fixture"), "ToString leaked tokens");
            Check(!Directory.EnumerateFiles(Path.GetDirectoryName(store.SessionPath)!).Any(x => x.EndsWith(".tmp")), "temporary session file left behind");
        }
        using (var restarted = new AccountService(store, new FakeAuth(request => Task.FromResult(Ok(request.RequestUri!.AbsolutePath.EndsWith("/user") ? User() : Profile())))))
        {
            await restarted.RestoreAsync();
            Check(restarted.State == AccountState.SignedIn && restarted.Nickname == "fixturepaw", "restart lost login");
        }

        foreach (var nickname in new[] { "", " ", "   ", "ab", " Paw", "Paw ", "Paw\t", "a\nb", "a\u200bb", "a\u00a0b", "a\u202eb", "_Paw", ".Paw", "😀Paw", new string('a', 25) })
            await Error(() => { AccountService.ValidateNickname(nickname); return Task.CompletedTask; }, "invalid_nickname");
        foreach(var nickname in new[]{"Пав","Ёжик","Пав-2","héllo","ｐａｗ","pаw"})
            await Error(()=>{AccountService.ValidateNickname(nickname);return Task.CompletedTask;},"invalid_nickname");
        foreach (var nickname in new[] { "Paw", "Paw_12", "Paw.Test", new string('a', 24) })
        { AccountService.ValidateNickname(nickname); checks++; }
        await Error(() => { AccountService.ValidateRegistration("bad", "long-password", "long-password", "Paw"); return Task.CompletedTask; }, "invalid_email");
        await Error(() => { AccountService.ValidateRegistration("x@example.invalid", "short", "short", "Paw"); return Task.CompletedTask; }, "weak_password");
        await Error(() => { AccountService.ValidateRegistration("x@example.invalid", "long-password", "other-password", "Paw"); return Task.CompletedTask; }, "password_mismatch");

        var registrationCalls = new List<string>();
        var registrationStore = Vault("registration");
        using (var registration = new AccountService(registrationStore, new FakeAuth(request =>
        {
            registrationCalls.Add(request.RequestUri!.AbsolutePath);
            if (request.RequestUri.AbsolutePath.EndsWith("signup"))
                Check(Uri.UnescapeDataString(request.RequestUri.Query) == "?redirect_to=" + AccountService.ConfirmationUrl, "signup confirmation redirect absent");
            return Task.FromResult(Ok(request.RequestUri.AbsolutePath.Contains("nickname_available") ? "true" : request.RequestUri.AbsolutePath.EndsWith("paw_registration_check")?"{\"status\":\"ok\"}":User()));
        })))
        {
            var signedIn = await registration.RegisterAsync("player@example.invalid", "fixture-secret-password", "fixture-secret-password", "NewPaw");
            Check(!signedIn && registration.State == AccountState.Guest && !File.Exists(registrationStore.SessionPath), "unconfirmed signup became authenticated");
            Check(registrationCalls.Count == 3 && registrationCalls[0].EndsWith("paw_nickname_available") && registrationCalls[1].EndsWith("paw_registration_check") && registrationCalls[2].EndsWith("signup"), "missing registration preflight");
        }
        using (var resend = new AccountService(Vault("resend"), new FakeAuth(request =>
        {
            Check(request.RequestUri!.AbsolutePath.EndsWith("resend") && Uri.UnescapeDataString(request.RequestUri.Query) == "?redirect_to=" + AccountService.ConfirmationUrl, "resend confirmation redirect absent");
            return Task.FromResult(Ok("{}"));
        }))) await resend.ResendConfirmationAsync("player@example.invalid");
        var taken = new FakeAuth(_ => Task.FromResult(Ok("false")));
        using (var registration = new AccountService(Vault("taken"), taken))
        {
            await Error(() => registration.RegisterAsync("p@example.invalid", "fixture-secret-password", "fixture-secret-password", "Paw"), "nickname_taken");
            Check(taken.Calls == 1, "taken nickname reached signup");
        }
        var raceCalls = 0;
        using (var registration = new AccountService(Vault("race"), new FakeAuth(_ => Task.FromResult(++raceCalls switch { 1 => Ok("true"), 2=>Ok("{\"status\":\"ok\"}"), 3 => Fail(500, "unexpected_failure"), _ => Ok("false") }))))
            await Error(() => registration.RegisterAsync("p@example.invalid", "fixture-secret-password", "fixture-secret-password", "Paw"), "nickname_taken");

        var expired = store.Read()!; expired.ExpiresAt = now.ToUnixTimeSeconds() - 1; store.Save(expired);
        var refreshes = 0;
        Func<HttpRequestMessage, Task<HttpResponseMessage>> refreshHandler = request =>
        {
            if (request.RequestUri!.Query.Contains("grant_type=refresh_token")) { Interlocked.Increment(ref refreshes); return Task.FromResult(Ok(Session("fixture-new-access", "fixture-new-refresh"))); }
            return Task.FromResult(Ok(request.RequestUri.AbsolutePath.EndsWith("/user") ? User() : Profile()));
        };
        using (var first = new AccountService(store, new FakeAuth(refreshHandler)))
        using (var second = new AccountService(store, new FakeAuth(refreshHandler)))
        {
            await Task.WhenAll(first.RestoreAsync(), second.RestoreAsync());
            Check(refreshes == 1, "two instances reused a rotated refresh token");
            Check(first.State == AccountState.SignedIn && second.State == AccountState.SignedIn, "concurrent restoration failed");
            Check(store.Read()!.RefreshToken == "fixture-new-refresh", "rotated refresh token not persisted");
        }
        var beforeOffline = await File.ReadAllBytesAsync(store.SessionPath);
        using (var offline = new AccountService(store, new FakeAuth(_ => throw new HttpRequestException("fixture-secret-server-detail"))))
        {
            await Error(() => offline.RestoreAsync(), "network");
            Check(offline.State == AccountState.Offline, "network failure became guest");
            Check(beforeOffline.SequenceEqual(await File.ReadAllBytesAsync(store.SessionPath)), "network failure erased saved session");
            Check(!await offline.SignOutAsync(), "offline logout claimed remote revocation");
            Check(offline.State == AccountState.Guest && !File.Exists(store.SessionPath), "offline logout did not clear local session");
            await offline.RestoreAsync(); Check(offline.State == AccountState.Guest, "offline logout auto-logged back in");
        }
        expired.ExpiresAt = now.ToUnixTimeSeconds() - 1; store.Save(expired);
        using (var revoked = new AccountService(store, new FakeAuth(_ => Task.FromResult(Fail(400, "refresh_token_not_found")))))
        {
            await Error(() => revoked.RestoreAsync(), "session_expired");
            Check(revoked.State == AccountState.Guest && !File.Exists(store.SessionPath), "revoked session retained");
        }
        var corrupt = Vault("corrupt"); Directory.CreateDirectory(Path.GetDirectoryName(corrupt.SessionPath)!); await File.WriteAllTextAsync(corrupt.SessionPath, "not a protected token");
        using (var service = new AccountService(corrupt, new FakeAuth(_ => throw new Exception("must not access network"))))
        {
            await Error(() => service.RestoreAsync(), "session_unreadable");
            Check(!File.Exists(corrupt.SessionPath), "unreadable session retained");
        }
        foreach (var (status, apiCode, code) in new[] { (400, "invalid_credentials", "invalid_credentials"), (400, "email_not_confirmed", "email_not_confirmed"), (429, "over_request_rate_limit", "rate_limit"), (400, "email_address_not_authorized", "mail_not_configured") })
        {
            using var service = new AccountService(Vault("failure-" + code), new FakeAuth(_ => Task.FromResult(Fail(status, apiCode))));
            await Error(() => service.SignInAsync("p@example.invalid", "fixture-secret-password"), code);
            Check(service.State == AccountState.Guest, "failed login became signed in");
        }
        using (var oversized = new AccountService(Vault("oversized"), new FakeAuth(_ => Task.FromResult(Ok(new string('x', 65537))))))
            await Error(() => oversized.SignInAsync("p@example.invalid", "fixture-secret-password"), "invalid_response");
        var lockStore = Vault("cancel");
        using (await lockStore.LockAsync(CancellationToken.None))
        using (var cancel = new CancellationTokenSource(50))
        {
            try { using var never = await lockStore.LockAsync(cancel.Token); throw new Exception("Lock cancellation ignored"); }
            catch (OperationCanceledException) { checks++; }
        }
        return checks;
    }

    internal static HttpResponseMessage Ok(string body) => new(HttpStatusCode.OK) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
    internal static HttpResponseMessage Fail(int status, string code) => new((HttpStatusCode)status) { Content = new StringContent(JsonSerializer.Serialize(new { error_code = code, message = "fixture-secret-server-detail" })) };
    internal sealed class FakeAuth(Func<HttpRequestMessage, Task<HttpResponseMessage>> response) : HttpMessageHandler
    {
        public int Calls;
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            // These legacy unit fixtures stub lease RPCs. Stateful ownership/races
            // are exercised separately by LauncherSessionTests with no bypass.
            if (request.RequestUri!.AbsolutePath.EndsWith("/paw_launcher_session")) return Ok("{\"status\":\"ok\"}");
            Interlocked.Increment(ref Calls); return await response(request);
        }
    }
}
