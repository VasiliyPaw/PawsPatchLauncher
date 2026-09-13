using System.Reflection;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class FixtureAccess
{
    internal static void AllowArcaneWars(MainWindow window)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated fixture required.");
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        var service = (AccountService)typeof(MainWindow).GetField("_account", flags)!.GetValue(window)!;
        var field = typeof(AccountService).GetField("_session", flags)!;
        var session = (AccountSession?)field.GetValue(service) ?? new AccountSession
        {
            UserId = "10000000-0000-4000-8000-000000000001", Nickname = "fixture",
            ExpiresAt = DateTimeOffset.UtcNow.AddHours(1).ToUnixTimeSeconds()
        };
        session.PawsTeam = true;
        field.SetValue(service, session);
        typeof(AccountService).GetProperty("State")!.SetValue(service, AccountState.SignedIn);
        typeof(MainWindow).GetMethod("RenderAccount", flags)!.Invoke(window, null);
    }
}
