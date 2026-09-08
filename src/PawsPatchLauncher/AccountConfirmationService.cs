using System.Net.Http;

namespace PawsPatchLauncher;

public sealed partial class AccountService
{
    public async Task ConfirmRegistrationAsync(string email, string code, bool remember, CancellationToken cancellationToken = default)
    {
        email = ValidateEmail(email);
        code = RecoveryCode.Normalize(code);
        if (!RecoveryCode.IsComplete(code)) throw new AccountException("invalid_confirmation_code");
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (_session is not null) throw new AccountException("sign_out_first");
            using var fileLock = await _store.LockAsync(cancellationToken).ConfigureAwait(false);
            using var verified = await RequestAsync(HttpMethod.Post, "verify", new { type = "email", email, token = code }, null, cancellationToken).ConfigureAwait(false);
            var session = ParseSession(verified.RootElement);
            if (!string.Equals(session.Email, email, StringComparison.OrdinalIgnoreCase))
                throw new AccountException("invalid_confirmation_code");
            cancellationToken.ThrowIfCancellationRequested();
            // Uses the same profile validation, single-launcher claim and encrypted
            // remember-me storage as password login. No password is retained for OTP.
            await EstablishLoginAsync(session, remember, cancellationToken).ConfigureAwait(false);
        }
        catch (AccountException error) when (error.Code == "invalid_recovery")
        { throw new AccountException("invalid_confirmation_code"); }
        finally { _gate.Release(); }
    }
}
