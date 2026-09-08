using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly DispatcherTimer _accountCooldownTimer = new();
    private string _accountEditor = "";
    private bool _accountRecoveryOpen;
    private bool _accountRecoverySent;
    private DateTimeOffset _recoveryRequestAfter;

    private void AccountHeader_Click(object sender, RoutedEventArgs e)
    {
        if (ConfirmationActive) return;
        SetActivePage("account");
        if (!_accountBusy)
        {
            _accountEditor = ""; _accountRecoveryOpen = false;
            ClearAccountPasswords(); RenderAccount();
            Motion.Reveal(_account.State == AccountState.Guest ? AccountFormCard : AccountSignedInCard);
        }
        MainOptionsScroll.ScrollToTop();
    }

    private void AccountRemember_Changed(object sender, RoutedEventArgs e)
    { if (_account is not null && _text is not null) RenderAccount(); }
    private async void AccountCopyUsername_Click(object sender,RoutedEventArgs e)
    {
        if(_account.State==AccountState.Guest||string.IsNullOrEmpty(_account.Nickname))return;
        var username=_account.Nickname;
        await AccountCopyUsernameButton.CopyAsync(()=>CopyTextAsync(username,()=>T("Username скопирован.","Username copied.")));
    }

    private void ApplyAccountProfileLanguage()
    {
        AccountForgotButton.Content = T("Забыли пароль?", "Forgot password?");
        AccountCopyUsernameButton.ToolTip=T("Скопировать username","Copy username");
        System.Windows.Automation.AutomationProperties.SetName(AccountCopyUsernameButton,AccountCopyUsernameButton.ToolTip.ToString());
        AccountEditNicknameButton.Content = T("Изменить username", "Change username");
        AccountEditDisplayNameButton.Content=T("Изменить имя", "Change display name");
        AccountEditEmailButton.Content = T("Изменить почту", "Change email");
        AccountEditPasswordButton.Content = T("Изменить пароль", "Change password");
        AccountCurrentPasswordLabel.Text = T("Текущий пароль", "Current password");
        AccountNewPasswordLabel.Text = AccountRecoveryPasswordLabel.Text = T("Новый пароль", "New password");
        AccountNewRepeatLabel.Text = AccountRecoveryRepeatLabel.Text = T("Повторите новый пароль", "Repeat new password");
        AccountEditorSubmitButton.Content = T("Сохранить изменения", "Save changes");
        AccountEditorCancelButton.Content = T("Отмена", "Cancel");
        AccountRecoveryTitleText.Text = T("Восстановление пароля", "Password recovery");
        AccountRecoveryEmailLabel.Text = T("Почта аккаунта", "Account email");
        AccountRecoveryProofLabel.Text = T("Код из письма · 6 цифр", "Email code · 6 digits");
        AccountRecoveryCancelButton.Content = T("Назад ко входу", "Back to sign in");
        foreach (var (control, label) in new (Control, string)[] {
            (AccountCurrentPasswordInput, AccountCurrentPasswordLabel.Text), (AccountNewPasswordInput, AccountNewPasswordLabel.Text),
            (AccountNewRepeatInput, AccountNewRepeatLabel.Text), (AccountRecoveryEmailInput, AccountRecoveryEmailLabel.Text),
            (AccountRecoveryProofInput, AccountRecoveryProofLabel.Text), (AccountRecoveryPasswordInput, AccountRecoveryPasswordLabel.Text),
            (AccountRecoveryRepeatInput, AccountRecoveryRepeatLabel.Text) })
            System.Windows.Automation.AutomationProperties.SetName(control, label);
    }

    private void RenderAccountProfile()
    {
        var guest = _account.State == AccountState.Guest;
        var online = _account.State == AccountState.SignedIn;
        var headerName = guest ? T("Гость", "Guest") : string.IsNullOrEmpty(_account.DisplayName) ? T("Игрок", "Player") : _account.DisplayName;
        if (AccountHeaderNameText.Text != headerName) { AccountHeaderNameText.Text = headerName; Motion.Reveal(AccountHeaderNameText); }
        AccountHeaderButton.ToolTip = guest ? T("Войти или зарегистрироваться", "Sign in or register") : T("Профиль: ", "Profile: ") + AccountHeaderNameText.Text;
        System.Windows.Automation.AutomationProperties.SetName(AccountHeaderButton, AccountHeaderButton.ToolTip.ToString());
        Motion.SetBackground(AccountAvatarBorder, (Brush)new BrushConverter().ConvertFrom(guest ? "#162A45" : "#594724")!);
        Motion.SetBorderBrush(AccountAvatarBorder, (Brush)FindResource(guest ? "TextMutedBrush" : "GoldBrush"));
        RenderAccountAvatar();
        AccountRememberText.Text = AccountRememberCheck.IsChecked == true
            ? T("Вход сохранится на этом компьютере. При следующем запуске пароль вводить не нужно.", "Stay signed in on this computer. No password is needed on the next launch.")
            : T("Вход только на этот запуск. После закрытия лаунчера нужно будет войти снова.", "Sign in for this launch only. You will need to sign in again after closing the launcher.");
        AccountRememberCheck.IsEnabled = AccountForgotButton.IsEnabled = !_accountBusy;
        AccountForgotButton.Visibility = !_accountRegister ? Visibility.Visible : Visibility.Collapsed;
        AccountCopyUsernameButton.SetContext(_account.UserId+"|"+_account.Nickname);
        AccountProfileCreatedText.Text = _account.CreatedAt is { } date ? T("Аккаунт создан: ", "Account created: ") + ChatDate(date) : "";
        AccountProfileCreatedText.Visibility = _account.CreatedAt is not null ? Visibility.Visible : Visibility.Collapsed;
        AccountEditDisplayNameButton.IsEnabled = AccountEditNicknameButton.IsEnabled = AccountEditEmailButton.IsEnabled = AccountEditPasswordButton.IsEnabled = online && !_accountBusy && !_account.Restricted;
        AccountEditorCard.Visibility = !guest && _accountEditor.Length > 0 ? Visibility.Visible : Visibility.Collapsed;
        AccountSignedInCard.Visibility = !guest && _accountEditor.Length == 0 ? Visibility.Visible : Visibility.Collapsed;
        AccountEditorFieldsPanel.IsEnabled = online && !_accountBusy && (!_account.Restricted||_accountEditor=="delete");
        AccountEditorCancelButton.IsEnabled = !_accountBusy;
        AccountEditValuePanel.Visibility = _accountEditor is "password" or "delete" ? Visibility.Collapsed : Visibility.Visible;
        AccountCurrentPasswordPanel.Visibility = _accountEditor is "nickname" or "display" ? Visibility.Collapsed : Visibility.Visible;
        AccountNewPasswordPanel.Visibility = _accountEditor == "password" ? Visibility.Visible : Visibility.Collapsed;
        AccountEditorShowPasswordCheck.Visibility = _accountEditor is "nickname" or "display" ? Visibility.Collapsed : Visibility.Visible;
        AccountEditValueLabel.Text = _accountEditor == "display"?T("Отображаемое имя","Display name"):_accountEditor=="nickname"? "Username":T("Новая почта","New email");
        AccountEditValueInput.MaxLength = _accountEditor == "nickname" ? 24 : _accountEditor=="display"?32:254;
        System.Windows.Automation.AutomationProperties.SetName(AccountEditValueInput, AccountEditValueLabel.Text);
        AccountEditorTitleText.Text = _accountEditor switch {
            "display"=>T("Отображаемое имя","Display name"), "nickname" => T("Изменение username", "Change username"), "email" => T("Изменение почты", "Change email"), "delete" => T("Удаление аккаунта", "Delete account"), _ => T("Изменение пароля", "Change password") };
        AccountEditorSubmitButton.Content = _accountEditor == "delete" ? T("Продолжить удаление…", "Continue deletion…") : T("Сохранить изменения", "Save changes");
        AccountEditorHintText.Text = _accountEditor switch {
            "display"=>T("До 32 символов. Это имя может совпадать у разных игроков.","Up to 32 characters. Other players can use the same name."),
            "nickname" => T("3–24 символа: английские буквы, цифры, точка, дефис и подчёркивание. Первый символ — буква или цифра. Смена раз в сутки.", "3–24 characters: English letters, digits, dots, hyphens and underscores. Start with a letter or digit. One change per day."),
            "email" => T("Укажите новый адрес и текущий пароль. Подтвердите смену через письма; до этого в профиле останется прежняя почта. Новый запрос на смену можно отправить через 5 минут.", "Enter your new email and current password. Confirm by email; your profile keeps the old address until then. Another change can be requested after 5 minutes."),
            "delete" => T("Аккаунт можно восстановить через администратора в течение 7 дней; username останется занят до окончательного удаления. Игра, патч и локальные сейвы останутся. Введите текущий пароль.", "An administrator can restore your account within 7 days; the username stays reserved until final deletion. The game, patch and local saves remain. Enter your current password."),
            _ => T("Подтвердите текущий пароль и задайте новый: 6-128 символов. Следующая смена будет доступна через 5 минут. Старые ссылки восстановления и смены почты станут недействительны; при необходимости запросите новые.", "Confirm your current password and choose a new one: 6-128 characters. Another change is available after 5 minutes. Old recovery and email-change links become invalid; request new ones if needed.") };
        AccountRecoveryCard.Visibility = guest && _accountRecoveryOpen ? Visibility.Visible : Visibility.Collapsed;
        AccountRecoveryFieldsPanel.IsEnabled = AccountRecoveryCancelButton.IsEnabled = !_accountBusy;
        AccountRecoveryEmailInput.IsEnabled = !_accountRecoverySent;
        AccountRecoveryProofPanel.Visibility = _accountRecoverySent ? Visibility.Visible : Visibility.Collapsed;
        AccountRecoveryShowPasswordCheck.Visibility = _accountRecoverySent ? Visibility.Visible : Visibility.Collapsed;
        AccountRecoverySubmitButton.Content = _accountRecoverySent ? T("Сохранить новый пароль", "Save new password") : T("Получить код", "Get a code");
        AccountRecoveryHintText.Text = _accountRecoverySent
            ? T("Введите 6-значный код из письма и задайте новый пароль.", "Enter the 6-digit email code and choose a new password.")
            : T("Отправим на почту одноразовый код для смены пароля.", "We will email you a one-time password reset code.");
        RenderAccountCooldown();
    }

    private void RenderAccountCooldown()
    {
        if (_account is null) return;
        var available = _accountEditor switch { "display"=>_account.DisplayNameChangeAvailableAt, "nickname" => _account.NicknameChangeAvailableAt, "email" => _account.EmailChangeAvailableAt, "password" => _account.PasswordChangeAvailableAt, _ => null };
        var remaining = available is { } until ? Math.Max(0, (int)Math.Ceiling((until - DateTimeOffset.UtcNow).TotalSeconds)) : 0;
        AccountCooldownText.Visibility = _accountEditor is "display" or "nickname" or "email" or "password" ? Visibility.Visible : Visibility.Collapsed;
        AccountCooldownText.Text = remaining > 0
            ? T("Следующая смена через ", "Next change in ") + $"{remaining/3600:00}:{remaining/60%60:00}:{remaining%60:00}"
            : T("Изменение доступно. У имени, username, почты и пароля отдельные таймеры.", "Change available. Display name, username, email and password have separate timers.");
        AccountEditorSubmitButton.IsEnabled = !_accountBusy && _account.State == AccountState.SignedIn && remaining == 0 && (_accountEditor != "nickname" || AccountService.NormalizeUsername(AccountEditValueInput.Text) != _account.Nickname);
        var resendSeconds = Math.Max(0, (int)Math.Ceiling((_recoveryRequestAfter - DateTimeOffset.UtcNow).TotalSeconds));
        AccountRecoverySubmitButton.IsEnabled = !_accountBusy && (_accountRecoverySent ? RecoveryCode.IsComplete(AccountRecoveryProofInput.Text) : resendSeconds == 0);
        AccountRecoveryResendButton.IsEnabled = !_accountBusy && resendSeconds == 0;
        AccountRecoveryResendButton.Content = resendSeconds > 0
            ? T("Новый код через ", "New code in ") + TimeSpan.FromSeconds(resendSeconds).ToString(@"mm\:ss")
            : T("Отправить код ещё раз", "Resend code");
    }

    private void AccountEdit_Click(object sender, RoutedEventArgs e) => ShowAccountEditor((string)((Button)sender).Tag);
    private void AccountEditorValue_Changed(object sender, TextChangedEventArgs e) { if (_account is not null) RenderAccountCooldown(); }
    private void ShowAccountEditor(string mode)
    {
        if (_accountBusy || ConfirmationActive || _account.State != AccountState.SignedIn || mode is not ("display" or "nickname" or "email" or "password" or "delete")) return;
        _accountEditor = mode; _accountMessage = ""; ClearAccountPasswords();
        AccountEditValueInput.Text = mode == "display"?_account.DisplayName:mode == "nickname" ? _account.Nickname : "";
        RenderAccount(); Motion.Reveal(AccountEditorCard); AccountEditorCard.BringIntoView();
        if (mode is "password" or "delete") AccountCurrentPasswordInput.Focus(); else AccountEditValueInput.Focus();
    }

    private void AccountEditorCancel_Click(object sender, RoutedEventArgs e)
    { if (_accountBusy) return; _accountEditor = ""; _accountMessage = ""; ClearAccountPasswords(); RenderAccount(); Motion.Reveal(AccountSignedInCard); }

    private async void AccountEditorSubmit_Click(object sender, RoutedEventArgs e) => await SubmitAccountEditorAsync();
    private async Task SubmitAccountEditorAsync()
    {
        if (_accountBusy || _accountEditor.Length == 0) return;
        var mode = _accountEditor; var value = AccountEditValueInput.Text;
        var current = AccountCurrentPasswordInput.Password; var password = AccountNewPasswordInput.Password; var repeat = AccountNewRepeatInput.Password;
        if (mode == "delete")
        {
            if (string.IsNullOrEmpty(current)) { _accountMessage = "current_password_required"; RenderAccount(); CardHighlight.Pulse(AccountMessageCard); return; }
            if (!await ConfirmActionAsync(T("Удалить аккаунт навсегда?", "Permanently delete account?"),
                T("Восстановление через администратора доступно 7 дней. Затем аккаунт удаляется окончательно. Игра, патч и локальные сохранения не удаляются.", "An administrator can restore the account within 7 days. It is then permanently deleted. The game, patch and local saves remain."),
                T("АККАУНТ", "ACCOUNT"), _account.Nickname + "\n" + _account.Email, T("Удалить аккаунт", "Delete account"))) { ClearAccountPasswords(); return; }
        }
        await AccountOperationAsync(async () =>
        {
            try
            {
                if (mode == "nickname") await _account.ChangeNicknameAsync(value, _accountLifetime.Token);
                else if (mode == "display") await _account.ChangeDisplayNameAsync(value,_accountLifetime.Token);
                else if (mode == "email") await _account.ChangeEmailAsync(value, current, _accountLifetime.Token);
                else if (mode == "password") await _account.ChangePasswordAsync(current, password, repeat, _accountLifetime.Token);
                else
                {
                    await _account.DeleteAccountAsync(current, _accountLifetime.Token);
                    AccountEmailInput.Clear(); AccountNicknameInput.Clear(); AccountDisplayNameInput.Clear(); _accountRegister = false; _accountConfirmation = false;
                }
                _accountMessage = mode == "delete" ? "account_deleted" : mode is "nickname" or "display" ? "nickname_changed" : mode == "email" ? "email_change_pending" : "password_changed";
                _accountEditor = ""; Motion.Reveal(AccountSignedInCard);
            }
            finally { ClearAccountPasswords(); }
        });
    }

    private void AccountForgot_Click(object sender, RoutedEventArgs e)
    {
        if (_accountBusy || ConfirmationActive) return;
        _accountRecoveryOpen = true; _accountRecoverySent = false; _accountMessage = "";
        AccountRecoveryEmailInput.Text = AccountEmailInput.Text;
        ClearAccountPasswords(); RenderAccount(); Motion.Reveal(AccountRecoveryCard); AccountRecoveryEmailInput.Focus();
    }
    private void AccountRecoveryCancel_Click(object sender, RoutedEventArgs e) => ShowAccountForm(register: false);
    private async void AccountRecoverySubmit_Click(object sender, RoutedEventArgs e) => await SubmitRecoveryAsync();
    private void AccountRecoveryCode_Changed(object sender, TextChangedEventArgs e)
    { if (_account is not null && AccountRecoverySubmitButton is not null) RenderAccountCooldown(); }

    private void AccountRecoveryCode_PreviewTextInput(object sender, TextCompositionEventArgs e)
    {
        var input = (TextBox)sender;
        var next = input.Text.Remove(input.SelectionStart, input.SelectionLength).Insert(input.SelectionStart, e.Text);
        e.Handled = !RecoveryCode.IsPartial(next);
    }

    private void AccountRecoveryCode_Pasting(object sender, DataObjectPastingEventArgs e)
    {
        if (e.DataObject.GetData(DataFormats.UnicodeText) is not string text) { e.CancelCommand(); return; }
        var code = RecoveryCode.Normalize(text);
        var input = (TextBox)sender;
        var next = input.Text.Remove(input.SelectionStart, input.SelectionLength).Insert(input.SelectionStart, code);
        if (code.Length == 0 || !RecoveryCode.IsPartial(next)) { e.CancelCommand(); return; }
        e.DataObject = new DataObject(DataFormats.UnicodeText, code);
        e.FormatToApply = DataFormats.UnicodeText;
    }

    private void AccountRecoveryCode_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter) return;
        e.Handled = true;
        if (RecoveryCode.IsComplete(AccountRecoveryProofInput.Text)) AccountRecoveryPasswordInput.Focus();
    }

    private async void AccountRecoveryResend_Click(object sender, RoutedEventArgs e) => await ResendRecoveryCodeAsync();
    private async Task ResendRecoveryCodeAsync()
    {
        if (_accountBusy || !_accountRecoverySent || ConfirmationActive || DateTimeOffset.UtcNow < _recoveryRequestAfter) return;
        await AccountOperationAsync(() => RequestRecoveryCodeAsync(AccountRecoveryEmailInput.Text));
        if (_accountMessage == "recovery_sent") AccountRecoveryProofInput.Focus();
    }

    private async Task RequestRecoveryCodeAsync(string email)
    {
        AccountService.ValidateEmail(email);
        _recoveryRequestAfter = DateTimeOffset.UtcNow.AddSeconds(60);
        await _account.RequestRecoveryAsync(email, _accountLifetime.Token);
        ClearAccountPasswords();
        var first = !_accountRecoverySent;
        _accountRecoverySent = true; _accountMessage = "recovery_sent";
        if (first) Motion.Reveal(AccountRecoveryProofPanel);
    }

    private async Task SubmitRecoveryAsync()
    {
        if (_accountBusy || (!_accountRecoverySent && DateTimeOffset.UtcNow < _recoveryRequestAfter)) return;
        var email = AccountRecoveryEmailInput.Text; var proof = AccountRecoveryProofInput.Text;
        var password = AccountRecoveryPasswordInput.Password; var repeat = AccountRecoveryRepeatInput.Password;
        await AccountOperationAsync(async () =>
        {
            if (!_accountRecoverySent)
            {
                await RequestRecoveryCodeAsync(email);
            }
            else
            {
                try
                {
                    var revoked = await _account.ResetPasswordAsync(email, proof, password, repeat, _accountLifetime.Token);
                    _accountRecoveryOpen = false; _accountRegister = false; _accountConfirmation = false;
                    AccountEmailInput.Text = email; _accountMessage = revoked ? "password_reset" : "password_reset_logout_pending";
                    Motion.Reveal(AccountFormCard);
                }
                finally { ClearAccountPasswords(); }
            }
        });
        if (_accountMessage == "recovery_sent") AccountRecoveryProofInput.Focus();
    }

    private string? ProfileAccountMessage(string code) => code switch
    {
        "avatar_saved" => T("Аватарка успешно изменена.", "Avatar updated successfully."),
        "avatar_removed" => T("Аватарка удалена.", "Avatar removed."),
        "invalid_avatar" => T("Не удалось прочитать изображение. Выберите обычный PNG или JPG до 8192 пикселей по стороне и 32 мегапикселей.", "Could not read the image. Choose a PNG or JPG up to 8192 pixels per side and 32 megapixels."),
        "avatar_too_large" => T("Изображение слишком большое. Выберите файл до 10 МБ; лаунчер уменьшит его перед отправкой.", "The image is too large. Choose a file up to 10 MB; the launcher reduces it before upload."),
        "account_deleted" => T("Аккаунт удалён. Игра и сохранения остались. Лаунчер работает в гостевом режиме.", "Account deleted. The game and saves remain. The launcher is in guest mode."),
        "account_busy" => T("Другое действие с аккаунтом ещё выполняется. Подождите немного и повторите.", "Another account action is still in progress. Wait a moment and retry."),
        "account_deletion_pending" => T("Удаление аккаунта ещё не завершено. Повторите удаление в профиле; остальные изменения временно недоступны.", "Account deletion is incomplete. Retry deletion in your profile; other changes are temporarily unavailable."),
        "outcome_unknown" => T("Сервер не подтвердил результат. Изменение могло выполниться. Проверьте профиль или вход перед повторной попыткой.", "The server did not confirm the result. The change may have completed. Check your profile or sign-in before retrying."),
        "email_cooldown" or "password_cooldown" => T("Следующее изменение будет доступно через 5 минут после предыдущего. Посмотрите таймер в форме.", "Another change is available 5 minutes after the previous one. Check the timer in the form."),
        "nickname_changed" => T("Имя обновлено.", "Name updated."),
        "nickname_cooldown" => T("Пока нельзя изменить ник. Подождите окончания таймера в форме; ограничение проверяется на сервере.", "Wait for the nickname timer in the form. This limit is checked by the server."),
        "email_change_pending" => T("Запрос отправлен. Подтвердите смену по письмам на текущую и новую почту. Адрес в профиле обновится после подтверждения сервером.", "Request sent. Confirm using the messages to your current and new email. Your profile updates after server confirmation."),
        "password_changed" => T("Пароль изменён. При следующем входе используйте новый пароль.", "Password changed. Use the new password the next time you sign in."),
        "recovery_sent" => T("Если аккаунт с этой почтой существует, придёт код восстановления. Проверьте также папку «Спам».", "If an account uses this email, a recovery code will arrive. Also check your spam folder."),
        "password_reset" => T("Новый пароль сохранён. Теперь войдите с почтой и новым паролем.", "Your new password is saved. Sign in with your email and new password."),
        "password_reset_logout_pending" => T("Пароль изменён. Сервер не подтвердил завершение всех прежних сеансов. Войдите с новым паролем.", "Password changed. Revocation of all earlier sessions was not confirmed. Sign in with the new password."),
        "invalid_recovery_code" => T("Введите 6 цифр из письма.", "Enter the 6 digits from the email."),
        "invalid_recovery" => T("Код недействителен или срок его действия истёк. Запросите новый код.", "The code is invalid or has expired. Request a new code."),
        "same_password" => T("Новый пароль должен отличаться от текущего.", "The new password must differ from the current one."),
        "same_email" => T("Этот адрес уже указан в профиле.", "This address is already in your profile."),
        "current_password_required" => T("Введите текущий пароль для подтверждения изменения.", "Enter the current password to confirm the change."),
        "email_unavailable" => T("Этот адрес нельзя использовать. Проверьте почту или восстановите доступ к существующему аккаунту.", "This address cannot be used. Check it or recover your existing account."),
        "reauthentication_needed" => T("Сервер требует повторного подтверждения. Выйдите и войдите с паролем, затем повторите изменение.", "Sign out and sign in with your password again, then retry the change."),
        "sign_out_first" => T("Сначала выйдите из аккаунта для восстановления входа.", "Sign out before recovering an account."),
        _ => null
    };
}
