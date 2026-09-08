using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Mail;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public sealed class AccountException(string code) : Exception("Account operation: " + code)
{
    public string Code { get; } = code;
}

public enum AccountState { Guest, SignedIn, Offline }

public sealed partial class AccountService : IDisposable
{
    public const string ProjectUrl = "https://trdzsdclscuwwmxnepyt.supabase.co";
    public const string ConfirmationUrl = "https://paws-patch-email-confirmation.vasiliypaw.chatgpt.site/";
    private static string WithConfirmationRedirect(string route) => route + "?redirect_to=" + Uri.EscapeDataString(ConfirmationUrl);
    // Supabase publishable key is intentionally public. Never substitute a secret/service_role key.
    public const string PublishableKey = "sb_publishable_wY4gkEMVpxwmFTllodpCeg_w_P1Uxal";
    private readonly HttpClient _http;
    private readonly AccountSessionStore _store;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly Func<DateTimeOffset> _clock;
    private AccountSession? _session;
    private DateTimeOffset _sessionVerifiedAt;
    private bool _remember = true;
    public bool Remembered => _remember;
    public DateTimeOffset? CreatedAt => _session?.CreatedAt;
    public DateTimeOffset? NicknameChangeAvailableAt => _session?.NicknameChangedAt?.AddDays(1);
    public DateTimeOffset? EmailChangeAvailableAt => _session?.EmailChangedAt?.AddMinutes(5);
    public DateTimeOffset? PasswordChangeAvailableAt => _session?.PasswordChangedAt?.AddMinutes(5);
    public DateTimeOffset? AvatarChangedAt => _session?.AvatarChangedAt;
    public bool DeletionPending => _session?.DeletionPending == true;
    public AccountState State { get; private set; }
    public string Email => _session?.Email ?? "";
    public static string NormalizeUsername(string value) => value.ToLowerInvariant();
    public string Nickname => NormalizeUsername(_session?.Nickname ?? "");
    public string DisplayName => string.IsNullOrEmpty(_session?.DisplayName)?_session?.Nickname??"":_session.DisplayName;
    public DateTimeOffset? DisplayNameChangeAvailableAt => _session?.DisplayNameChangedAt?.AddMinutes(5);
    public string UserId => _session?.UserId ?? "";

    public AccountService(AccountSessionStore store, HttpMessageHandler? handler = null, Func<DateTimeOffset>? clock = null)
    {
        _store = store;
        _clock = clock ?? (() => DateTimeOffset.UtcNow);
        _http = new HttpClient(handler ?? new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = Timeout.InfiniteTimeSpan };
    }

    public static string ValidateEmail(string value)
    {
        var email = value.Trim();
        if (email.Length is < 3 or > 254 || !MailAddress.TryCreate(email, out var parsed) || parsed.Address != email || !email.Contains('@') || email.Any(char.IsControl))
            throw new AccountException("invalid_email");
        return email;
    }

    public static void ValidateRegistration(string email, string password, string confirmation, string nickname)
    {
        ValidateEmail(email);
        if (password.Length is < 6 or > 128) throw new AccountException("weak_password");
        if (password != confirmation) throw new AccountException("password_mismatch");
        ValidateNickname(nickname);
    }

    public static void ValidateNickname(string nickname)
    {
        // Match the server exactly. No trimming: surrounding spaces are errors, not aliases.
        if (!Regex.IsMatch(nickname, "\\A[A-Za-z0-9][A-Za-z0-9_.-]{2,23}\\z", RegexOptions.CultureInvariant))
            throw new AccountException("invalid_nickname");
    }
    public static void ValidateDisplayName(string value)
    {
        if(string.IsNullOrWhiteSpace(value)||value!=value.Trim()||value.EnumerateRunes().Count()>32
            ||value.Any(c=>char.IsControl(c)||char.GetUnicodeCategory(c)==System.Globalization.UnicodeCategory.Format))
            throw new AccountException("invalid_display_name");
    }

    public async Task<bool> IsNicknameAvailableAsync(string nickname, CancellationToken cancellationToken = default)
    {
        ValidateNickname(nickname);
        using var response = await RequestAsync(HttpMethod.Post, "rpc/paw_nickname_available", new { candidate = NormalizeUsername(nickname) }, null, cancellationToken, database: true).ConfigureAwait(false);
        if (response.RootElement.ValueKind is not (JsonValueKind.True or JsonValueKind.False)) throw new AccountException("invalid_response");
        return response.RootElement.GetBoolean();
    }

    private async Task LoadProfileAsync(CancellationToken cancellationToken)
    {
        using var response = await RequestAsync(HttpMethod.Get, "paw_profiles?select=id,nickname,display_name,display_name_changed_at,created_at,nickname_changed_at,email_changed_at,password_changed_at,avatar_changed_at,deletion_pending,admin_level,protected_admin,banned_at,ban_until,ban_reason,deleted_at&id=eq." + _session!.UserId, null, _session.AccessToken, cancellationToken, database: true).ConfigureAwait(false);
        if (response.RootElement.ValueKind != JsonValueKind.Array || response.RootElement.GetArrayLength() != 1) throw new AccountException("profile_missing");
        var profile = response.RootElement[0];
        if (Text(profile, "id") != _session.UserId) throw new AccountException("invalid_response");
        var nickname = Text(profile, "nickname"); ValidateNickname(nickname);
        _session.Nickname = NormalizeUsername(nickname);
        _session.DisplayName=Text(profile,"display_name");if(_session.DisplayName.Length==0)_session.DisplayName=nickname;
        ValidateDisplayName(_session.DisplayName);
        _session.DisplayNameChangedAt=DateTimeOffset.TryParse(Text(profile,"display_name_changed_at"),out var displayChanged)?displayChanged:null;
        _session.CreatedAt = DateTimeOffset.TryParse(Text(profile, "created_at"), out var created) ? created : null;
        _session.NicknameChangedAt = DateTimeOffset.TryParse(Text(profile, "nickname_changed_at"), out var changed) ? changed : null;
        _session.EmailChangedAt = DateTimeOffset.TryParse(Text(profile, "email_changed_at"), out var emailChanged) ? emailChanged : null;
        _session.PasswordChangedAt = DateTimeOffset.TryParse(Text(profile, "password_changed_at"), out var passwordChanged) ? passwordChanged : null;
        _session.AvatarChangedAt = DateTimeOffset.TryParse(Text(profile, "avatar_changed_at"), out var avatarChanged) ? avatarChanged : null;
        _session.DeletionPending = profile.TryGetProperty("deletion_pending", out var deleting) && deleting.ValueKind == JsonValueKind.True;
        _session.AdminLevel = ModerationInt(profile,"admin_level");
        _session.ProtectedAdmin = ModerationBool(profile,"protected_admin");
        _session.BannedAt = ModerationDate(profile,"banned_at");
        _session.BanUntil = ModerationDate(profile,"ban_until");
        _session.BanReason = Text(profile,"ban_reason");
        _session.DeletedAt = ModerationDate(profile,"deleted_at");
        if (_remember && _launcherClaimed) _store.Save(_session);
        State = AccountState.SignedIn;
    }

    public async Task SignInAsync(string email, string password, CancellationToken cancellationToken = default, bool remember = true)
    {
        email=email.Trim();
        var username=email.StartsWith('@')?email[1..]:email;
        var byUsername=!username.Contains('@');
        if(byUsername){ValidateNickname(username);username=NormalizeUsername(username);}else email=ValidateEmail(email);
        if (password.Length is < 1 or > 128) throw new AccountException("invalid_credentials");
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            using var fileLock = await _store.LockAsync(cancellationToken).ConfigureAwait(false);
            using var response = byUsername
                ? await RequestAsync(HttpMethod.Post,"username-login",new{username,password},null,cancellationToken,portal:true).ConfigureAwait(false)
                : await RequestAsync(HttpMethod.Post, "token?grant_type=password", new { email, password }, null, cancellationToken).ConfigureAwait(false);
            cancellationToken.ThrowIfCancellationRequested();
            var session = ParseSession(response.RootElement);
            await EstablishLoginAsync(session, remember, cancellationToken).ConfigureAwait(false);
        }
        finally { _gate.Release(); }
    }

    // true only if the server actually returned a session (e.g. local test Auth).
    // Hosted email confirmation normally means no session and no authenticated UI.
    public async Task<bool> RegisterAsync(string email, string password, string confirmation, string nickname, CancellationToken cancellationToken = default, bool remember = true,string? displayName=null)
    {
        ValidateRegistration(email, password, confirmation, nickname);
        displayName ??= nickname;ValidateDisplayName(displayName);
        nickname=NormalizeUsername(nickname);
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            using var fileLock = await _store.LockAsync(cancellationToken).ConfigureAwait(false);
            if (!await IsNicknameAvailableAsync(nickname, cancellationToken).ConfigureAwait(false)) throw new AccountException("nickname_taken");
            using(var eligibility=await RequestAsync(HttpMethod.Post,"rpc/paw_registration_check",new{address=email.Trim(),candidate=nickname},null,cancellationToken,database:true).ConfigureAwait(false))
            {
                var status=Text(eligibility.RootElement,"status");
                if(status!="ok")throw new AccountException(status is "email_banned" or "invalid_nickname" or "invalid_email"?status:"service_error");
            }
            JsonDocument response;
            try { response = await RequestAsync(HttpMethod.Post, WithConfirmationRedirect("signup"), new { email = email.Trim(), password, data = new { nickname,display_name=displayName } }, null, cancellationToken).ConfigureAwait(false); }
            catch (AccountException error) when (error.Code is "network" or "service_error")
            {
                // The unique DB constraint is the authority for concurrent registrations.
                bool? stillFree = null;
                try { stillFree = await IsNicknameAvailableAsync(nickname, cancellationToken).ConfigureAwait(false); }
                catch (AccountException) { }
                if (stillFree == false) throw new AccountException("nickname_taken");
                string? eligibilityStatus=null;
                try
                {
                    using var eligibility=await RequestAsync(HttpMethod.Post,"rpc/paw_registration_check",new{address=email.Trim(),candidate=nickname},null,cancellationToken,database:true).ConfigureAwait(false);
                    eligibilityStatus=Text(eligibility.RootElement,"status");
                }
                catch(AccountException) { }
                if(eligibilityStatus=="email_banned")throw new AccountException("email_banned");
                throw;
            }
            using var registration = response;
            if (!response.RootElement.TryGetProperty("access_token", out var token) || string.IsNullOrEmpty(token.GetString())) return false;
            cancellationToken.ThrowIfCancellationRequested();
            var session = ParseSession(response.RootElement);
            await EstablishLoginAsync(session, remember, cancellationToken).ConfigureAwait(false);
            return true;
        }
        finally { _gate.Release(); }
    }

    public async Task ResendConfirmationAsync(string email, CancellationToken cancellationToken = default)
    {
        email = ValidateEmail(email);
        using var response = await RequestAsync(HttpMethod.Post, WithConfirmationRedirect("resend"), new { type = "signup", email }, null, cancellationToken).ConfigureAwait(false);
    }

    public async Task RestoreAsync(CancellationToken cancellationToken = default, bool reuseRecent = false)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            using var fileLock = await _store.LockAsync(cancellationToken).ConfigureAwait(false);
            try { ReadOwnedSession(); }
            catch (Exception error) when (error is System.Security.Cryptography.CryptographicException or InvalidDataException or JsonException)
            { _store.Clear(); SetGuest(); throw new AccountException("session_unreadable"); }
            if (_session is null) { SetGuest(); return; }
            // Always check protected local ownership above. Server RPCs still authorize every action.
            // Only the redundant Auth/profile round trip is shared for at most 30 seconds.
            var now = _clock();
            if (reuseRecent && _launcherClaimed && State == AccountState.SignedIn
                && now >= _sessionVerifiedAt && now - _sessionVerifiedAt < TimeSpan.FromSeconds(30)
                && _session.ExpiresAt > now.ToUnixTimeSeconds() + 90) return;
            try
            {
                if (_session.ExpiresAt <= _clock().ToUnixTimeSeconds() + 90) await RefreshAsync(cancellationToken).ConfigureAwait(false);
                else
                {
                    try
                    {
                        using var user = await RequestAsync(HttpMethod.Get, "user", null, _session.AccessToken, cancellationToken).ConfigureAwait(false);
                        ReadUser(user.RootElement, _session, _session.UserId);
                    }
                    catch (AccountException error) when (error.Code == "unauthorized") { await RefreshAsync(cancellationToken).ConfigureAwait(false); }
                }
                if (!_launcherClaimed) await ClaimLauncherAsync("resume", cancellationToken).ConfigureAwait(false);
                else await LauncherRequestAsync("check", cancellationToken).ConfigureAwait(false);
                await LoadProfileAsync(cancellationToken).ConfigureAwait(false);
                _sessionVerifiedAt = _clock();
            }
            catch (AccountException error) when (error.Code is "session_expired" or "session_replaced")
            { ClearOwnedSession(); SetGuest(); throw; }
            catch (AccountException)
            { if (_session is not null) State = AccountState.Offline; throw; }
        }
        finally { _gate.Release(); }
    }

    private async Task RefreshAsync(CancellationToken cancellationToken)
    {
        try
        {
            using var response = await RequestAsync(HttpMethod.Post, "token?grant_type=refresh_token", new { refresh_token = _session!.RefreshToken }, null, cancellationToken).ConfigureAwait(false);
            var updated = ParseSession(response.RootElement);
            if (updated.UserId != _session.UserId) throw new AccountException("invalid_response");
            updated.Nickname = _session.Nickname;
            updated.CreatedAt = _session.CreatedAt;
            updated.NicknameChangedAt = _session.NicknameChangedAt;
            updated.EmailChangedAt = _session.EmailChangedAt;
            updated.PasswordChangedAt = _session.PasswordChangedAt;
            updated.AvatarChangedAt = _session.AvatarChangedAt;
            updated.DeletionPending = _session.DeletionPending;
            updated.LauncherId = _session.LauncherId; updated.LoginId = _session.LoginId;
            cancellationToken.ThrowIfCancellationRequested();
            SaveSession(updated);
        }
        catch (AccountException error) when (error.Code is "unauthorized" or "session_expired" or "invalid_credentials")
        { ClearOwnedSession(); SetGuest(); throw new AccountException("session_expired"); }
    }

    public async Task<string> GetAccessTokenAsync(CancellationToken cancellationToken = default)
    {
        // Re-read protected storage every time: another launcher may have logged out/rotated tokens.
        await RestoreAsync(cancellationToken).ConfigureAwait(false);
        var session = _session;
        if (session is null || State != AccountState.SignedIn) throw new AccountException("session_expired");
        return session.AccessToken;
    }

    public async Task<bool> SignOutAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            using var fileLock = await _store.LockAsync(cancellationToken).ConfigureAwait(false);
            // Remove local credentials before contacting the server; offline logout stays logged out.
            var previous = _session;
            ClearOwnedSession();
            if (previous is null) return true;
            try
            {
                // Release first. An old window sharing this Auth session must not
                // revoke the newer window's session through Auth logout.
                await LauncherRequestAsync("release", cancellationToken).ConfigureAwait(false);
                using var response = await RequestAsync(HttpMethod.Post, "logout?scope=local", null, previous.AccessToken, cancellationToken).ConfigureAwait(false);
                return true;
            }
            catch (AccountException error) when (error.Code is "unauthorized" or "session_replaced" or "session_expired") { return true; }
            catch (AccountException) { return false; }
            finally { SetGuest(); }
        }
        finally { _gate.Release(); }
    }

    private void SaveSession(AccountSession session) { if (_remember && (_launcherClaimed || SameStoredLogin(_store.Read()))) _store.Save(session); _session = session; State = AccountState.SignedIn; }
    private void SetGuest() { _session = null; _launcherClaimed = false; _sessionVerifiedAt = default; State = AccountState.Guest; }

    private AccountSession ParseSession(JsonElement data)
    {
        var access = Text(data, "access_token");
        var refresh = Text(data, "refresh_token");
        var seconds = data.TryGetProperty("expires_in", out var expires) && expires.TryGetInt64(out var lifetime) ? lifetime : 0;
        if (access.Length is < 1 or > 16384 || refresh.Length is < 1 or > 16384 || seconds is <= 0 or > 604800 || !data.TryGetProperty("user", out var user))
            throw new AccountException("invalid_response");
        var session = new AccountSession { AccessToken = access, RefreshToken = refresh, ExpiresAt = _clock().ToUnixTimeSeconds() + seconds };
        ReadUser(user, session);
        return session;
    }

    private static void ReadUser(JsonElement user, AccountSession session, string? expectedId = null)
    {
        var id = Text(user, "id");
        if (!Guid.TryParse(id, out _) || expectedId is not null && expectedId != id || Text(user, "email").Length > 254)
            throw new AccountException("invalid_response");
        session.UserId = id; session.Email = Text(user, "email");
        // Nicknames come only from the unique server profile, never mutable user_metadata.
    }

    private static string Text(JsonElement item, string key) => item.ValueKind == JsonValueKind.Object && item.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() ?? "" : "";

    private async Task<JsonDocument> RequestAsync(HttpMethod method, string route, object? body, string? accessToken, CancellationToken cancellationToken, bool database = false, bool portal = false)
    {
        using var request = new HttpRequestMessage(method, new Uri(ProjectUrl + (portal ? "/functions/v1/" : database ? "/rest/v1/" : "/auth/v1/") + route));
        request.Headers.Add("apikey", PublishableKey);
        if (accessToken is not null && (database || portal)) request.Headers.Add("x-paw-launcher", _launcherId.ToString());
        if (accessToken is not null) request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        if (body is not null) request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromSeconds(portal ? 90 : 15));
            using var response = await _http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token).ConfigureAwait(false);
            if (!portal && (int)response.StatusCode >= 500) throw new AccountException("network");
            await using var source = await response.Content.ReadAsStreamAsync(timeout.Token).ConfigureAwait(false);
            using var output = new MemoryStream();
            var buffer = new byte[4096];
            int count;
            while ((count = await source.ReadAsync(buffer, timeout.Token).ConfigureAwait(false)) != 0)
            {
                if (output.Length + count > (portal ? 350000 : database && route is "rpc/paw_read_messages" or "rpc/paw_read_message_page" or "rpc/paw_read_offer_states" ? 768000 : database&&route=="rpc/paw_social_list"?2097152:database&&route=="rpc/paw_admin_list"?262144:65536)) throw new AccountException("invalid_response");
                output.Write(buffer, 0, count);
            }
            JsonDocument json;
            try { json = output.Length == 0 ? JsonDocument.Parse("{}") : JsonDocument.Parse(output.ToArray()); }
            catch (JsonException) when ((int)response.StatusCode == 429) { throw new AccountException("rate_limit"); }
            if ((int)response.StatusCode == 429)
            {
                var errorCode = Text(json.RootElement, "error_code");
                if (errorCode.Length == 0) errorCode = Text(json.RootElement, "code");
                json.Dispose();
                throw new AccountException(errorCode == "over_email_send_rate_limit" ? "email_rate_limit" : "rate_limit");
            }
            if (portal)
            {
                var status = Text(json.RootElement, "status");
                if (response.IsSuccessStatusCode && status == "ok") return json;
                json.Dispose();
                throw new AccountException(status switch {
                    "unauthorized" or "session_replaced" or "session_expired" or "invalid_credentials" or "email_not_confirmed" or "email_cooldown" or "password_cooldown" or "account_busy"
                    or "account_deletion_pending" or "confirmation_required" or "invalid_avatar" or "avatar_too_large"
                    or "current_password_required" or "invalid_email" or "same_email" or "same_password" or "weak_password"
                    or "email_unavailable" or "reauthentication_needed" or "rate_limit" or "outcome_unknown" or "friend_required"
                    or "account_banned" or "email_banned" or "protected_account" => status,
                    "service_unavailable" => "network", _ => "service_error" });
            }
            if (response.IsSuccessStatusCode) return json;
            using (json)
            {
                var code = Text(json.RootElement, "error_code");
                // Never expose/log raw server bodies: these can contain personal input or credentials.
                throw new AccountException(code switch
                {
                    "invalid_credentials" => "invalid_credentials",
                    "email_not_confirmed" => "email_not_confirmed",
                    "otp_expired" or "otp_disabled" => "invalid_recovery",
                    "same_password" => "same_password",
                    "reauthentication_needed" or "reauthentication_not_valid" => "reauthentication_needed",
                    "email_exists" or "user_already_exists" => "email_unavailable",
                    "weak_password" => "weak_password",
                    "email_address_invalid" => "invalid_email",
                    "email_address_not_authorized" => "mail_not_configured",
                    "over_email_send_rate_limit" => "email_rate_limit",
                    "over_request_rate_limit" => "rate_limit",
                    "refresh_token_not_found" or "refresh_token_already_used" or "session_not_found" => "session_expired",
                    "signup_disabled" => "signup_disabled",
                    "captcha_failed" => "captcha_required",
                    _ when response.StatusCode == HttpStatusCode.Unauthorized => "unauthorized",
                    _ => "service_error"
                });
            }
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested) { throw new AccountException(portal ? "outcome_unknown" : "network"); }
        catch (HttpRequestException) { throw new AccountException(portal ? "outcome_unknown" : "network"); }
        catch (JsonException) { throw new AccountException("invalid_response"); }
    }

    public void Dispose() { _session = null; _http.Dispose(); }
}
