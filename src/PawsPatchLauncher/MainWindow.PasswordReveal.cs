using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly List<(PasswordBox Secret, TextBox Visible, CheckBox Toggle)> _passwordPairs = [];
    private bool _passwordSync;

    private void InitializePasswordReveal()
    {
        foreach (var (name, toggle) in new[] {
            ("AccountPasswordInput", AccountShowPasswordCheck), ("AccountRepeatInput", AccountShowPasswordCheck),
            ("AccountCurrentPasswordInput", AccountEditorShowPasswordCheck), ("AccountNewPasswordInput", AccountEditorShowPasswordCheck), ("AccountNewRepeatInput", AccountEditorShowPasswordCheck),
            ("AccountRecoveryPasswordInput", AccountRecoveryShowPasswordCheck), ("AccountRecoveryRepeatInput", AccountRecoveryShowPasswordCheck) })
        {
            var secret = (PasswordBox)FindName(name); var visible = (TextBox)FindName(name + "Visible");
            _passwordPairs.Add((secret, visible, toggle));
            secret.PasswordChanged += (_, _) =>
            {
                if (_passwordSync) return;
                _passwordSync = true;
                try { visible.Text = toggle.IsChecked == true ? secret.Password : ""; }
                finally { _passwordSync = false; }
            };
            visible.TextChanged += (_, _) =>
            {
                if (_passwordSync || toggle.IsChecked != true) return;
                _passwordSync = true;
                try { secret.Password = visible.Text; }
                finally { _passwordSync = false; }
            };
        }
    }

    private void ApplyPasswordRevealLanguage()
    {
        foreach (var toggle in new[] { AccountShowPasswordCheck, AccountEditorShowPasswordCheck, AccountRecoveryShowPasswordCheck })
            toggle.Content = T("Показать пароль", "Show password");
        foreach (var pair in _passwordPairs)
            System.Windows.Automation.AutomationProperties.SetName(pair.Visible,
                System.Windows.Automation.AutomationProperties.GetName(pair.Secret) + T(" (показан)", " (visible)"));
    }

    private void ShowPassword_Changed(object sender, RoutedEventArgs e)
    {
        if (_passwordSync) return;
        _passwordSync = true;
        try
        {
            foreach (var pair in _passwordPairs.Where(p => ReferenceEquals(p.Toggle, sender)))
            {
                var show = pair.Toggle.IsChecked == true;
                pair.Visible.Text = show ? pair.Secret.Password : "";
                pair.Visible.Visibility = show ? Visibility.Visible : Visibility.Collapsed;
                pair.Secret.Visibility = show ? Visibility.Collapsed : Visibility.Visible;
            }
        }
        finally { _passwordSync = false; }
    }

    private void ResetPasswordReveal()
    {
        foreach (var pair in _passwordPairs) { pair.Visible.Clear(); pair.Toggle.IsChecked = false; }
    }

    private static bool AccountSuccess(string code) => code is "signed_in" or "signed_out" or "nickname_changed" or "password_changed" or "password_reset" or "account_deleted" or "avatar_saved" or "avatar_removed";
    private static bool AccountInformation(string code) => code is "confirmation_sent" or "email_not_confirmed" or "email_change_pending" or "recovery_sent" or "nickname_cooldown" or "email_cooldown" or "password_cooldown" or "account_busy";

    private void UpdateAccountMessageAppearance()
    {
        var success = AccountSuccess(_accountMessage);
        var informational = AccountInformation(_accountMessage);
        var border = success ? "#4D9B75" : informational ? "#D9B34F" : "#C97764";
        var fill = success ? "#142F28" : informational ? "#302B1D" : "#332024";
        Motion.SetBorderBrush(AccountMessageCard, (Brush)new BrushConverter().ConvertFrom(border)!);
        Motion.SetBackground(AccountMessageCard, (Brush)new BrushConverter().ConvertFrom(fill)!);
        AccountMessageIcon.Kind = success ? IconKind.Check : IconKind.Warning;
        AccountMessageIcon.Foreground = (Brush)new BrushConverter().ConvertFrom(success ? "#79D9AA" : informational ? "#F0CC73" : "#FFA891")!;
        AccountMessageText.Foreground = (Brush)FindResource("TextMainBrush");
    }
}
