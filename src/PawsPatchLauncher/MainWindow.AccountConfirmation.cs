using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private bool _confirmationRemember = true;

    private void BeginEmailConfirmation()
    {
        _accountConfirmation = true;
        _confirmationRemember = AccountRememberCheck.IsChecked == true;
        AccountConfirmationEmailInput.Text = AccountEmailInput.Text.Contains('@') ? AccountEmailInput.Text : "";
        AccountConfirmationCodeInput.Clear();
        ClearAccountPasswords();
    }

    private void RenderEmailConfirmation()
    {
        if (AccountConfirmationCard is null) return;
        var visible = _account.State == AccountState.Guest && _accountConfirmation && !_accountRecoveryOpen;
        AccountConfirmationCard.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
        AccountConfirmationTitle.Text = T("Подтвердите почту", "Confirm your email");
        AccountConfirmationHint.Text = T("Введите код из письма — после подтверждения вы сразу войдёте в аккаунт.", "Enter the email code to confirm your address and sign in.");
        AccountConfirmationEmailLabel.Text = T("Почта аккаунта", "Account email");
        AccountConfirmationCodeLabel.Text = T("Код из письма · 6 цифр", "Email code · 6 digits");
        AccountConfirmButton.Content = T("Подтвердить и войти", "Confirm and sign in");
        AccountConfirmationBackButton.Content = T("Назад ко входу", "Back to sign in");
        AccountConfirmButton.IsEnabled = !_accountBusy && RecoveryCode.IsComplete(AccountConfirmationCodeInput.Text);
        AccountConfirmationEmailInput.IsEnabled = AccountConfirmationCodeInput.IsEnabled = AccountConfirmationBackButton.IsEnabled = !_accountBusy;
        System.Windows.Automation.AutomationProperties.SetName(AccountConfirmationCodeInput, AccountConfirmationCodeLabel.Text);
        System.Windows.Automation.AutomationProperties.SetName(AccountConfirmationEmailInput, AccountConfirmationEmailLabel.Text);
    }
    private void AccountConfirmationCode_Changed(object sender, TextChangedEventArgs e)
    { if (_account is not null) RenderEmailConfirmation(); }
    private async void AccountConfirmationCode_KeyDown(object sender, KeyEventArgs e)
    { if (e.Key == Key.Enter) { e.Handled = true; await ConfirmEmailAsync(); } }
    private async void AccountConfirm_Click(object sender, RoutedEventArgs e) => await ConfirmEmailAsync();
    private async Task ConfirmEmailAsync()
    {
        if (!_accountConfirmation || !RecoveryCode.IsComplete(AccountConfirmationCodeInput.Text)) return;
        var email = AccountConfirmationEmailInput.Text;
        var code = AccountConfirmationCodeInput.Text;
        await AccountOperationAsync(async () =>
        {
            await _account.ConfirmRegistrationAsync(email, code, _confirmationRemember, _accountLifetime.Token);
            _accountConfirmation = false; _accountRegister = false; _accountMessage = "signed_in";
            AccountConfirmationCodeInput.Clear();
            ClearAccountPasswords();
            Motion.Reveal(AccountSignedInCard);
            await RefreshAccountAvatarAsync();
        });
    }
}
