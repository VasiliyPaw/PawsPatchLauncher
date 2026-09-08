using System.Net.Http;
using System.Text.Json;
using PawsPatchLauncher;
using static AccountTests;

internal static class AccountProfileTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var checks = 0;
        void Check(bool ok, string why) { checks++; if (!ok) throw new Exception("Account profile: " + why); }
        async Task Error(Func<Task> action, string code)
        {
            try { await action(); throw new Exception("Expected " + code); }
            catch (AccountException error) { Check(error.Code == code, error.Code + " instead of " + code); }
        }
        var id = Guid.NewGuid().ToString();
        AccountService.ValidateNewPassword("123456", "123456"); checks++;
        AccountService.ValidateRegistration("qa@example.invalid", "123456", "123456", "Paw"); checks++;
        await Error(() => { AccountService.ValidateNewPassword("12345", "12345"); return Task.CompletedTask; }, "weak_password");
        await Error(() => { AccountService.ValidateNewPassword("123456", "123457"); return Task.CompletedTask; }, "password_mismatch");
        var now = DateTimeOffset.UtcNow;
        var name = "ProfilePaw"; DateTimeOffset? changed = null; DateTimeOffset? emailChanged = null; DateTimeOffset? passwordChanged = null;
        string User(string email = "qa@example.invalid") => JsonSerializer.Serialize(new { id, email });
        string Session(string email = "qa@example.invalid") => "{\"access_token\":\"qa-access\",\"refresh_token\":\"qa-refresh\",\"expires_in\":120,\"user\":" + User(email) + "}";
        string Profile() => JsonSerializer.Serialize(new[] { new { id, nickname = name, created_at = now.AddDays(-2), nickname_changed_at = changed, email_changed_at = emailChanged, password_changed_at = passwordChanged } });
        AccountSessionStore Vault(string key) => new(Path.Combine(root, "account-profile", key));
        var tokenRequests = 0; var mutationRequests = 0; var wrongPassword = false; var nicknameStatus = "ok";
        var handler = new FakeAuth(async request =>
        {
            Check(request.RequestUri!.GetLeftPart(UriPartial.Authority) == AccountService.ProjectUrl, "wrong fixed origin");
            Check(request.Headers.GetValues("apikey").Single() == AccountService.PublishableKey, "wrong key");
            var route = request.RequestUri.AbsolutePath;
            if (route.EndsWith("/token"))
            {
                tokenRequests++;
                Check(request.Headers.Authorization is null, "credentials sent with unrelated bearer");
                if (wrongPassword && request.RequestUri.Query.Contains("grant_type=password")) return Fail(400, "invalid_credentials");
                return Ok(Session());
            }
            if (route.Contains("paw_profiles")) return Ok(Profile());
            if (route.EndsWith("paw_change_nickname"))
            {
                mutationRequests++; Check(request.Headers.Authorization?.Parameter == "qa-access", "rename not authenticated");
                using var body = JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                if (nicknameStatus == "ok") { name = body.RootElement.GetProperty("candidate").GetString()!; changed = now; }
                return Ok(JsonSerializer.Serialize(new { status = nicknameStatus, retry_after = 300 }));
            }
            if (route.EndsWith("/account-actions"))
            {
                Check(request.Headers.Authorization?.Parameter == "qa-access", "account action not authenticated");
                using var body = JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                if (wrongPassword) return Ok("{\"status\":\"invalid_credentials\"}");
                Check(body.RootElement.GetProperty("current_password").GetString() == "fixture-current-password", "current password missing");
                var action = body.RootElement.GetProperty("action").GetString();
                if (action == "email" && emailChanged is not null) return Ok("{\"status\":\"email_cooldown\"}");
                if (action == "password" && passwordChanged is not null) return Ok("{\"status\":\"password_cooldown\"}");
                mutationRequests++;
                if (action == "email") emailChanged = now;
                if (action == "password") passwordChanged = now;
                if (action == "password") return Ok("{\"status\":\"ok\",\"session\":" + Session() + "}");
                return Ok("{\"status\":\"ok\"}"); // email stays old while server confirmation is pending
            }
            return Ok(User());
        });
        var vault = Vault("ephemeral");
        using (var account = new AccountService(vault, handler, () => now))
        {
            await account.SignInAsync("qa@example.invalid", "fixture-current-password");
            Check(File.Exists(vault.SessionPath), "default remember is not on");
            await account.SignInAsync("qa@example.invalid", "fixture-current-password", remember: false);
            Check(!account.Remembered && !File.Exists(vault.SessionPath), "unchecked remember persisted credentials");
            await account.RestoreAsync();
            Check(account.State == AccountState.SignedIn, "memory session disappeared on restore");
            now = now.AddMinutes(2); var before = tokenRequests;
            await account.RestoreAsync();
            Check(tokenRequests == before + 1 && !File.Exists(vault.SessionPath), "memory refresh lost privacy");
            await account.ChangeNicknameAsync("NewPaw");
            Check(account.Nickname == "newpaw" && account.NicknameChangeAvailableAt == now.AddDays(1), "nickname/timer not read from profile");
            Check(account.CreatedAt is not null && !File.Exists(vault.SessionPath), "profile data absent or ephemeral token persisted");
            nicknameStatus = "nickname_cooldown";
            await Error(() => account.ChangeNicknameAsync("NextPaw"), "nickname_cooldown");
            nicknameStatus = "nickname_taken";
            await Error(() => account.ChangeNicknameAsync("TakenPaw"), "nickname_taken");
            await Error(() => account.ChangeNicknameAsync("   "), "invalid_nickname");
            var writes = mutationRequests; wrongPassword = true;
            await Error(() => account.ChangeEmailAsync("new@example.invalid", "wrong-password"), "invalid_credentials");
            Check(mutationRequests == writes, "wrong password reached email mutation"); wrongPassword = false;
            await account.ChangeEmailAsync("new@example.invalid", "fixture-current-password");
            Check(account.Email == "qa@example.invalid", "pending email presented as confirmed");
            Check(account.EmailChangeAvailableAt == now.AddMinutes(5), "email cooldown not read from server");
            await Error(() => account.ChangeEmailAsync("another@example.invalid", "fixture-current-password"), "email_cooldown");
            await account.ChangePasswordAsync("fixture-current-password", "fixture-new-password", "fixture-new-password");
            Check(account.PasswordChangeAvailableAt == now.AddMinutes(5), "password cooldown not read from server");
            await Error(() => account.ChangePasswordAsync("fixture-current-password", "fixture-other-password", "fixture-other-password"), "password_cooldown");
            await Error(() => account.ChangePasswordAsync("fixture-current-password", "fixture-current-password", "fixture-current-password"), "same_password");
            await Error(() => account.ChangePasswordAsync("", "fixture-new-password", "fixture-new-password"), "current_password_required");
            Check(!File.Exists(vault.SessionPath), "sensitive operation persisted ephemeral session");
        }
        using (var restart = new AccountService(vault, new FakeAuth(_ => throw new Exception("ephemeral restart must not access network"))))
        { await restart.RestoreAsync(); Check(restart.State == AccountState.Guest, "unchecked remember survived restart"); }

        var signupVault = Vault("signup-ephemeral");
        using (var signup = new AccountService(signupVault, new FakeAuth(r => Task.FromResult(Ok(r.RequestUri!.AbsolutePath.Contains("nickname_available") ? "true" : r.RequestUri.AbsolutePath.EndsWith("paw_registration_check")?"{\"status\":\"ok\"}":r.RequestUri.AbsolutePath.EndsWith("signup") ? Session() : Profile())))))
        {
            Check(await signup.RegisterAsync("qa@example.invalid", "fixture-new-password", "fixture-new-password", "ProfilePaw", remember: false), "autoconfirm signup failed");
            Check(!File.Exists(signupVault.SessionPath), "unchecked signup persisted token");
        }

        var recoveryVault = Vault("recovery"); var recoveryRequests = new List<string>(); var mismatched = false;
        var recoveryTokens = new List<string>(); var expired = false;
        using (var recovery = new AccountService(recoveryVault, new FakeAuth(async request =>
        {
            recoveryRequests.Add(request.RequestUri!.PathAndQuery);
            Check(request.RequestUri.GetLeftPart(UriPartial.Authority) == AccountService.ProjectUrl, "recovery followed untrusted link");
            if (request.RequestUri.AbsolutePath.EndsWith("/verify"))
            {
                using var body = JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                Check(body.RootElement.GetProperty("type").GetString() == "recovery", "wrong OTP purpose");
                Check(body.RootElement.GetProperty("email").GetString() == "qa@example.invalid", "OTP not bound to email");
                Check(!body.RootElement.TryGetProperty("token_hash", out _), "link/hash accepted as recovery code");
                recoveryTokens.Add(body.RootElement.GetProperty("token").GetString()!);
                Check(request.Headers.Authorization is null, "recovery reused ordinary bearer");
                if (expired) return new HttpResponseMessage(System.Net.HttpStatusCode.Forbidden) { Content = new StringContent("{\"error_code\":\"otp_expired\"}") };
                return Ok(Session(mismatched ? "other@example.invalid" : "qa@example.invalid"));
            }
            if (request.Method == HttpMethod.Put)
            { Check(request.Headers.Authorization?.Parameter == "qa-access", "password reset not tied to recovery session"); return Ok(User()); }
            return Ok("{}");
        })))
        {
            await recovery.RequestRecoveryAsync("qa@example.invalid");
            Check(recoveryRequests.Single().EndsWith("/recover"), "recovery not requested");
            Check(await recovery.ResetPasswordAsync("qa@example.invalid", "123456", "fixture-new-password", "fixture-new-password"), "OTP reset failed");
            Check(recoveryRequests.Any(r => r.Contains("scope=global")), "recovery did not request old-session revocation");
            Check(recovery.State == AccountState.Guest && !File.Exists(recoveryVault.SessionPath), "recovery became persisted login");
            Check(await recovery.ResetPasswordAsync("qa@example.invalid", " 001 234\r\n", "fixture-new-password", "fixture-new-password"), "spaced code reset failed");
            Check(recoveryTokens.Last() == "001234", "leading zeroes or whitespace normalization lost");
            var link = AccountService.ProjectUrl + "/auth/v1/verify?token=" + new string('a', 64) + "&type=recovery&redirect_to=https%3A%2F%2Fexample.invalid";
            mismatched = true; var before = recoveryRequests.Count;
            await Error(() => recovery.ResetPasswordAsync("qa@example.invalid", "123456", "fixture-new-password", "fixture-new-password"), "invalid_recovery");
            Check(recoveryRequests.Skip(before).Count() == 2 && recoveryRequests.Last().Contains("logout?scope=local"), "mismatched recovery changed password or kept token");
            foreach (var proof in new[] { "", "123", "12345", "1234567", "12345678", "abcdef", "１２３４５６", "١٢٣٤٥٦", "12-3456", "Code: 123456", new string('1', 4097), link, "https://evil.invalid/auth/v1/verify?token=" + new string('a', 64) + "&type=recovery", link.Replace("type=recovery", "type=signup"), link + "&type=recovery", link + "#access_token=secret", link.Replace("https:", "http:") })
            {
                before = recoveryRequests.Count;
                await Error(() => recovery.ResetPasswordAsync("qa@example.invalid", proof, "fixture-new-password", "fixture-new-password"), "invalid_recovery_code");
                Check(recoveryRequests.Count == before, "invalid proof reached network");
            }
            mismatched = false; expired = true; before = recoveryRequests.Count;
            await Error(() => recovery.ResetPasswordAsync("qa@example.invalid", "123456", "fixture-new-password", "fixture-new-password"), "invalid_recovery");
            Check(recoveryRequests.Count == before + 1 && recoveryRequests.Last().EndsWith("/verify"), "expired code reached password mutation");
            Check(recovery.State == AccountState.Guest && !File.Exists(recoveryVault.SessionPath), "failed recovery retained session");
        }
        Console.WriteLine($"ACCOUNT PROFILE PASS {checks}: remember on/off, refresh/restart, nickname and cooldown, reauthentication, pending email, recovery purpose/origin/isolation; no real email or credentials");
        return checks;
    }
}
