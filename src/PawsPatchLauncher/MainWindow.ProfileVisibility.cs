using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private ProfileVisibility? _profileVisibility;
    private string? _visibilityOwner, _visibilityRequestOwner, _visibilityLanguage;
    private bool _visibilityReady, _visibilityBusy;
    private DateTimeOffset _visibilityReadAt, _visibilityRetryAfter;
    private Func<ProfileVisibility?, CancellationToken, Task<ProfileVisibility>>? _visibilityOverride = null;
    private static readonly string[] VisibilityValues = ["all", "friends", "nobody"];

    private void InitializeProfileVisibility() { _visibilityReady = true; RefreshProfileVisibility(); }
    private void RefreshProfileVisibility()
    {
        if (!_visibilityReady) return;
        ProfileVisibilityTitle.Text = T("Видимость профиля", "Profile visibility");
        ProfileVisibilityDescription.Text = T("Выберите, кто видит игровые настройки и подробную активность. Имя, аватарка и общий статус останутся видимыми. Блокировка закрывает профиль.",
            "Choose who can see gameplay settings and detailed activity. Your name, avatar and general status remain visible. Blocking hides the profile.");
        ConfigurationVisibilityLabel.Text = T("Игровые настройки и компоненты", "Gameplay settings and components");
        ActivityVisibilityLabel.Text = T("Подробная игровая активность", "Detailed game activity");
        SaveProfileVisibilityButton.Content = T("Сохранить", "Save");
        if (_visibilityLanguage != _text.Language)
        {
            foreach (var combo in new[] { ConfigurationVisibilityCombo, ActivityVisibilityCombo })
            {
                var selection = Math.Max(0, combo.SelectedIndex); combo.Items.Clear();
                foreach (var label in new[] { T("Всем", "Everyone"), T("Только друзьям", "Friends only"), T("Никому", "Nobody") }) combo.Items.Add(new SettingOption(label));
                combo.SelectedIndex = selection;
            }
            _visibilityLanguage = _text.Language;
        }
        var owner = _account.UserId;
        var signed = _account.State == AccountState.SignedIn && !_account.Restricted && !AccountConnectionBlocked;
        if (_visibilityOwner != owner) _profileVisibility = null;
        ConfigurationVisibilityCombo.IsEnabled = ActivityVisibilityCombo.IsEnabled = signed && !_visibilityBusy && _profileVisibility is not null;
        SaveProfileVisibilityButton.IsEnabled = signed && !_visibilityBusy && _profileVisibility is not null;
        if (!signed) ProfileVisibilityStatus.Text = T("Войдите в аккаунт, чтобы изменить видимость. Настройки сохраняются для аккаунта на сервере.",
            "Sign in to change visibility. These settings are saved for your account on the server.");
        if (signed && !_visibilityBusy && _activePage == "account" && !ActivityStore.IsSmokeTest
            && ShouldRefreshProfileVisibility(owner, DateTimeOffset.UtcNow))
            _ = LoadProfileVisibilityAsync();
    }

    private bool ShouldRefreshProfileVisibility(string owner, DateTimeOffset now)
    {
        if (_visibilityRequestOwner != owner) return true;
        if (now < _visibilityRetryAfter) return false;
        return _profileVisibility is null || now - _visibilityReadAt > TimeSpan.FromMinutes(1)
            && ConfigurationVisibilityCombo.SelectedIndex == Array.IndexOf(VisibilityValues, _profileVisibility.Configuration)
            && ActivityVisibilityCombo.SelectedIndex == Array.IndexOf(VisibilityValues, _profileVisibility.Activity);
    }

    private async Task LoadProfileVisibilityAsync()
    {
        if (_visibilityBusy || _account.State != AccountState.SignedIn) return;
        var owner = _account.UserId; _visibilityRequestOwner = owner; _visibilityBusy = true;
        ProfileVisibilityStatus.Text = T("Загружаю настройки аккаунта…", "Loading account settings…"); RefreshProfileVisibility();
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token); timeout.CancelAfter(TimeSpan.FromSeconds(10));
            var value = await (_visibilityOverride?.Invoke(null, timeout.Token) ?? _account.ReadProfileVisibilityAsync(timeout.Token));
            if (_account.UserId != owner) return;
            _visibilityOwner = owner; _profileVisibility = value; _visibilityReadAt = DateTimeOffset.UtcNow; _visibilityRetryAfter = default;
            ConfigurationVisibilityCombo.SelectedIndex = Array.IndexOf(VisibilityValues, value.Configuration);
            ActivityVisibilityCombo.SelectedIndex = Array.IndexOf(VisibilityValues, value.Activity);
            ProfileVisibilityStatus.Text = T("Настройки аккаунта загружены. Изменения применяются после сохранения.", "Account settings loaded. Save to apply changes.");
        }
        catch (Exception error) when (error is AccountException or OperationCanceledException or System.Net.Http.HttpRequestException)
        {
            if (_account.UserId == owner)
            {
                _visibilityRetryAfter = DateTimeOffset.UtcNow.AddSeconds(30);
                ProfileVisibilityStatus.Text = T("Не удалось загрузить настройки. Повторим автоматически. Видимость не изменена.",
                    "Could not load settings. Retrying automatically. Visibility has not changed.");
            }
        }
        finally { _visibilityBusy = false; RefreshProfileVisibility(); }
    }
    private async void SaveProfileVisibility_Click(object sender, RoutedEventArgs e) => await SaveProfileVisibilityAsync();
    private async Task SaveProfileVisibilityAsync()
    {
        if (_visibilityBusy || _account.State != AccountState.SignedIn || _visibilityOwner != _account.UserId || _profileVisibility is null) return;
        var value = new ProfileVisibility(VisibilityValues[Math.Max(0, ConfigurationVisibilityCombo.SelectedIndex)], VisibilityValues[Math.Max(0, ActivityVisibilityCombo.SelectedIndex)]);
        var owner = _account.UserId; _visibilityBusy = true; RefreshProfileVisibility();
        ProfileVisibilityStatus.Text = T("Сохраняю…", "Saving…");
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token); timeout.CancelAfter(TimeSpan.FromSeconds(10));
            var saved = await (_visibilityOverride?.Invoke(value, timeout.Token) ?? _account.SaveProfileVisibilityAsync(value, timeout.Token));
            if (_account.UserId != owner) return;
            _profileVisibility = saved; _visibilityReadAt = DateTimeOffset.UtcNow;
            ProfileVisibilityStatus.Text = T("Сохранено для аккаунта. Другие игроки увидят изменения при обновлении профиля.", "Saved for your account. Other players will see changes when their profile view refreshes.");
            _socialPresenceNext = default;
        }
        catch (Exception error) when (error is AccountException or OperationCanceledException or System.Net.Http.HttpRequestException)
        {
            if (_account.UserId == owner) ProfileVisibilityStatus.Text = T("Не удалось сохранить. Прежняя видимость остаётся в силе. Повторите попытку.", "Could not save. Your previous visibility remains in effect. Try again.");
        }
        finally { _visibilityBusy = false; RefreshProfileVisibility(); }
    }
}
