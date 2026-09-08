using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private sealed class FriendCopyException(Func<string> message) : Exception
    {
        public Func<string> LocalizedMessage { get; } = message;
    }
    private string? _socialDetailsLayoutKey;
    private int _socialDetailsGeneration;
    // Deterministic smoke-test seams; normal runtime uses authenticated RPCs and the transactional installer.
    private Func<Task<IReadOnlyList<SocialPlayer>>>? _friendSettingsReadOverride = null;
    private Func<string, Task<ChannelManifest?>>? _friendSettingsFeedOverride = null;
    private Func<ChannelManifest, UserSettings, Func<Task>, Task>? _friendSettingsApplyOverride = null;

    private void CloseSocialDetails()
    {
        _socialDetailsGeneration++;
        Motion.Collapse(SocialDetailsOverlay);
        SocialDetailsCard.IsEnabled=true;
        _socialDetailsPeer = null; _socialDetailsLayoutKey = null;
        _adminViewedPlayer=null;
        SocialDetailsCopyUsernameButton.SetContext("");
        SocialDetailsAvatar.Content = null; SocialDetailsName.Text = SocialDetailsUsername.Text = "";
        SocialDetailsStatus.Text = SocialDetailsActivity.Text = SocialDetailsChannel.Text = "";
        SocialDetailsComponents.Children.Clear();
    }

    private async void SocialDetailsClose_Click(object sender, RoutedEventArgs e) => await DismissSocialDetailsAsync();
    private async Task DismissSocialDetailsAsync()
    {
        if(ConfirmationActive)return;
        var generation=_socialDetailsGeneration;
        SocialDetailsCard.IsEnabled=false;
        if(await Motion.HideAsync(SocialDetailsOverlay) && generation==_socialDetailsGeneration)CloseSocialDetails();
    }

    private void ShowSocialDetails(SocialPlayer player)
    {
        if (player.Deleted || (player.Relation != "friend" || !_socialPlayers.Any(p => p.Id == player.Id && p.Relation == "friend"))&& !(_account.AdminLevel>0&&_adminViewedPlayer?.Id==player.Id)) return;
        _socialDetailsGeneration++;
        _socialDetailsPeer = player.Id; RenderSocialDetails(player);
        SocialDetailsCard.IsEnabled=true;
        SocialDetailsOverlay.Visibility = Visibility.Visible;
        SocialDetailsOverlay.UpdateLayout(); Motion.Reveal(SocialDetailsOverlay);
        SocialDetailsClose.Focus();
    }

    private void RenderSocialDetails(SocialPlayer player)
    {
        SocialDetailsName.Text = player.Name;
        SocialDetailsAdminBadge.Content=player.AdminLevel>0?AdministratorBadge(player.AdminLevel,inline:false):null;
        SocialDetailsModerationText.Text=player.Banned?BanDescription(player.BannedAt,player.BanUntil,player.BanReason):player.CreatedAt is DateTimeOffset registered?T("Регистрация: ","Registered: ")+ChatDate(registered):"";
        SocialDetailsModerationText.Foreground=SocialBrush(player.Banned?"#FFB6B6":"#A8BBD2");
        SocialDetailsModerationText.Visibility=SocialDetailsModerationText.Text.Length>0?Visibility.Visible:Visibility.Collapsed;
        SocialDetailsUsername.Text="@"+player.Nickname;
        SocialDetailsCopyUsernameButton.SetContext(player.Id+"|"+player.Nickname);
        SocialDetailsCopyUsernameButton.ToolTip=T("Скопировать username","Copy username");
        System.Windows.Automation.AutomationProperties.SetName(SocialDetailsCopyUsernameButton,SocialDetailsCopyUsernameButton.ToolTip.ToString());
        var presence=player.Available?player.Presence:"offline";
        SocialDetailsStatus.Text = SocialStatusName(presence);
        SocialDetailsStatus.Foreground = SocialBrush(presence == "playing" ? "#62DCA6" : presence == "online" ? "#82B5FF" : "#A8BBD2");
        SocialDetailsActivity.Text = "";
        if (presence == "playing" && player.PlayingSince is DateTimeOffset started)
        {
            var duration = DateTimeOffset.UtcNow - started; if (duration < TimeSpan.Zero) duration = TimeSpan.Zero;
            SocialDetailsActivity.Text = T("В игре: ", "Playing for: ") + (duration.TotalHours >= 1 ? $"{(int)duration.TotalHours} " + T("ч ", "h ") : "") + $"{(int)duration.TotalMinutes % 60} " + T("мин", "min");
        }
        else if (presence == "offline")
            SocialDetailsActivity.Text = player.LastSeen is DateTimeOffset seen ? T("Был в сети: ", "Last seen: ") + ChatDate(seen) : T("Время последнего входа неизвестно", "Last seen time unavailable");
        SocialDetailsChannelLabel.Text = T("Канал патча", "Patch channel");
        SocialDetailsChannel.Text = player.Channel == "beta" ? T("Бета", "Beta") : player.Channel == "stable" ? T("Релиз", "Release") : T("Неизвестен", "Unknown");
        SocialDetailsComponentsLabel.Text = T(player.Presence == "offline" ? "ПОСЛЕДНИЕ НАСТРОЙКИ" : "КОМПОНЕНТЫ", player.Presence == "offline" ? "LAST KNOWN SETTINGS" : "COMPONENTS");
        SocialDetailsCopyButton.Content = T("Скопировать конфигурацию", "Copy configuration");
        SocialDetailsRemoveButton.Content=T("Удалить из друзей","Remove friend");
        SocialDetailsBlockButton.Content=T("Заблокировать","Block");
        SocialDetailsClose.ToolTip = T("Закрыть", "Close");
        System.Windows.Automation.AutomationProperties.SetName(SocialDetailsClose, T("Закрыть", "Close"));
        var key = $"{player.Id}|{player.Components}|{player.Configuration}|{player.Presence}|{player.Available}|{_socialAvatarGeneration}|{_text.Language}";
        if (_socialDetailsLayoutKey != key)
        {
            _socialDetailsLayoutKey = key;
            SocialDetailsAvatar.Content = SocialAvatar(player.Id, 68, true);
            SocialDetailsComponents.Children.Clear();
            var exact = FriendConfiguration.TryParse(player.Configuration, player.Channel, out var settings);
            using var data = JsonDocument.Parse(player.Components);
            // Use the actual Components tab labels and its visual order, not JSON property order.
            foreach (var (name, title) in new[] {
                ("core", CoreTitleText), ("russian", RussianTitleText), ("colors", ColorsTitleText),
                ("desync", OosTitleText), ("hostility", IndependentTitleText), ("roaming", RoamingSpawnTitleText),
                ("additional_roaming", AdditionalRoamingTitleText), ("siege", SiegeBalanceTitleText),
                ("powers_shards", PowersShardsTitleText) })
            {
                if (!data.RootElement.TryGetProperty(name, out var item) || item.ValueKind is not (JsonValueKind.True or JsonValueKind.False)) continue;
                var label = title.Text;
                var enabled = item.GetBoolean();
                var value = exact && name == "roaming" ? settings.RoamingSpawnMode switch { "x2" => "×2", "x4" => "×4", _ => "×1" } : T(enabled ? "Вкл." : "Выкл.", enabled ? "On" : "Off");
                var row = new Grid { Margin = new Thickness(0, 0, 0, 4) };
                row.ColumnDefinitions.Add(new ColumnDefinition());
                row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
                // One continuous surface connects each label with its value without adding height.
                var surface = new Border { Background = SocialBrush("#1D334B"), CornerRadius = new CornerRadius(5), IsHitTestVisible = false };
                Grid.SetColumnSpan(surface, 2); row.Children.Add(surface);
                row.Children.Add(new TextBlock { Text = label, FontSize = 13, TextWrapping = TextWrapping.Wrap, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(8, 0, 12, 0) });
                var chip = new Border { Background = SocialBrush(enabled ? "#183E38" : "#233248"), CornerRadius = new CornerRadius(5), MinWidth = 48, Padding = new Thickness(8, 4, 8, 4),
                    Child = new TextBlock { Text = value, Foreground = SocialBrush(enabled ? "#76DAB0" : "#A0B0C4"), FontSize = 12, HorizontalAlignment = HorizontalAlignment.Center } };
                Grid.SetColumn(chip, 1); row.Children.Add(chip);
                SocialDetailsComponents.Children.Add(row);
            }
            if (SocialDetailsComponents.Children.Count == 0)
                SocialDetailsComponents.Children.Add(new TextBlock { Text = T("Пока нет данных", "No data yet"), Foreground = SocialBrush("#A8BBD2") });
        }
        RefreshSocialCopyAvailability();
        SocialDetailsComponents.Visibility=SocialDetailsChannel.Visibility=SocialDetailsChannelLabel.Visibility=SocialDetailsComponentsLabel.Visibility=player.Available?Visibility.Visible:Visibility.Collapsed;
    }

    private void RefreshSocialCopyAvailability()
    {
        var player = _socialPlayers.FirstOrDefault(p => p.Id == _socialDetailsPeer && p.Relation == "friend");
        var exact = player is not null && FriendConfiguration.TryParse(player.Configuration, player.Channel, out _);
        var available = player?.Available == true && !_account.Restricted;
        var hint = !available ? "" : !exact ? T("Другу нужно открыть новую версию лаунчера с установленным патчем.", "Your friend needs to open the new launcher with the patch installed.")
            : ConfigurationMatches(player!.Configuration) ? T("Конфигурация уже совпадает.", "Configuration already matches.")
            : _game is null ? T("Сначала выберите папку игры.", "Select the game folder first.")
            : IsGameRunning() ? T("Закройте игру, чтобы применить настройки.", "Close the game to apply settings.")
            : _account.State != AccountState.SignedIn ? T("Для копирования нужно подключение к аккаунту.", "Connect to your account to copy settings.") : "";
        SocialDetailsCopyHint.Text = hint;
        SocialDetailsCopyButton.Visibility = available ? Visibility.Visible : Visibility.Collapsed;
        SocialDetailsCopyHint.Visibility = hint.Length == 0 ? Visibility.Collapsed : Visibility.Visible;
        SocialDetailsCopyButton.IsEnabled = exact && player?.Available==true && !_account.Restricted && hint.Length == 0 && !_busy && !FeedBlocksActions && !_accountBusy && !_socialBusy && !ConfirmationActive;
        SocialDetailsRemoveButton.IsEnabled=SocialDetailsBlockButton.IsEnabled=player is not null&&_account.State==AccountState.SignedIn
            &&!_busy&&!FeedBlocksActions&&!_accountBusy&&!_socialBusy&&!ConfirmationActive;
        SocialDetailsRemoveButton.IsEnabled&=player?.IsFriend==true&&player?.Deleted==false&&!_account.Restricted;
        SocialDetailsBlockButton.IsEnabled&=player?.AdminLevel==0&&player?.Deleted==false&&!_account.Restricted;
    }

    private async void SocialDetailsCopy_Click(object sender, RoutedEventArgs e) => await CopyFriendSettingsAsync();
    private async void SocialDetailsCopyUsername_Click(object sender,RoutedEventArgs e)
    {
        var player=_socialPlayers.FirstOrDefault(p=>p.Id==_socialDetailsPeer&&p.Relation=="friend")??(_account.AdminLevel>0?_adminViewedPlayer:null);
        if(player is null)return;
        await SocialDetailsCopyUsernameButton.CopyAsync(()=>CopyTextAsync(player.Nickname,()=>T("Username скопирован.","Username copied.")));
    }
    private async void SocialDetailsFriendAction_Click(object sender,RoutedEventArgs e)
    {
        if(sender is not Button {Tag:string action}||action is not ("remove" or "block")||ConfirmationActive||_busy)return;
        var player=_socialPlayers.FirstOrDefault(p=>p.Id==_socialDetailsPeer&&p.Relation=="friend");
        if(player is not null)await SocialFriendActionAsync(player,action);
    }

    private Task CopyFriendSettingsAsync()
    {
        var player = _socialPlayers.FirstOrDefault(p => p.Id == _socialDetailsPeer && p.Relation == "friend");
        return player is null ? Task.CompletedTask : CopyConfigurationAsync(player);
    }

    private async Task CopyConfigurationAsync(SocialPlayer? player, SocialOffer? offer = null)
    {
        if (player is null || !FriendConfiguration.TryParse(player.Configuration, player.Channel, out var imported)
            || _game is null || _busy || FeedBlocksActions || _accountBusy || _socialBusy || ConfirmationActive || _account.State != AccountState.SignedIn) return;
        var owner = _account.UserId;
        var originalCode = player.Configuration;
        OfferReceipt? receipt = null; var succeeded = false;
        RoutedEventHandler? localizationChanged = null;
        try
        {
            EnsureGameClosed();
            if(ConfigurationMatches(originalCode)) return;
            var baseline=LocalAppliedConfiguration();
            var incomingLocalization = imported.RussianLocalization;
            var changeLocalization = incomingLocalization != baseline.RussianLocalization;
            var confirmation = ConfirmActionAsync(T("Скопировать конфигурацию?", "Copy configuration?"),
                T("Изменения будут сразу применены к игре. Сохранения останутся на месте.", "Changes will be applied to the game immediately. Saves will be kept."),
                T("ЧТО ИЗМЕНИТСЯ", "WHAT WILL CHANGE"), "", T("Скопировать и применить", "Copy and apply"));
            ConfirmationLocalizationToggle.Content = T("Менять локализацию", "Change localization");
            ConfirmationLocalizationToggle.Visibility = changeLocalization ? Visibility.Visible : Visibility.Collapsed;
            void UpdateChanges()
            {
                imported.RussianLocalization = !changeLocalization || ConfirmationLocalizationToggle.IsChecked == true ? incomingLocalization : baseline.RussianLocalization;
                RenderConfigurationChanges(baseline,imported);
                ConfirmationDeleteButton.IsEnabled = !ConfigurationMatches(ConfigurationCode.Create(imported));
            }
            localizationChanged = (_,_) => UpdateChanges();
            ConfirmationLocalizationToggle.Checked += localizationChanged;
            ConfirmationLocalizationToggle.Unchecked += localizationChanged;
            UpdateChanges();
            LauncherIcon.SetKind(ConfirmationDeleteButton, IconKind.Copy); ConfirmationActionIcon.Kind = IconKind.Copy;
            ConfirmationDeleteButton.Background = SocialBrush("#80662F"); ConfirmationDeleteButton.BorderBrush = SocialBrush("#D5AE52");
            Motion.SetHoverBackground(ConfirmationDeleteButton, SocialBrush("#A3833D")); Motion.SetPressedBackground(ConfirmationDeleteButton, SocialBrush("#695425"));
            if (!await confirmation) return;
            CloseSocialDetails();
            SetBusy(true, T("Применяю конфигурацию…", "Applying configuration…"));
            ShowToast(() => T("Началось применение конфигурации друга.", "Applying your friend's configuration."));
            if (offer is not null) receipt = await BeginOfferApplicationAsync(offer);
            async Task Revalidate()
            {
                if (_account.UserId != owner || _account.State != AccountState.SignedIn) throw new AccountException("session_expired");
                var friends = _friendSettingsReadOverride is not null ? await _friendSettingsReadOverride() : await _account.GetFriendsAsync(_accountLifetime.Token);
                if (_account.UserId != owner || _account.State != AccountState.SignedIn) throw new AccountException("session_expired");
                var fresh = friends.FirstOrDefault(p => p.Id == player.Id && p.Relation == "friend");
                if (fresh is null || offer is null && (fresh.Configuration != originalCode || fresh.Channel != player.Channel))
                    throw new FriendCopyException(() => T("Данные друга изменились. Откройте профиль и повторите.", "Your friend's details changed. Open their profile and try again."));
                if (receipt is not null) await VerifyOfferApplicationAsync(receipt);
                EnsureGameClosed();
            }
            await Revalidate();
            var channel = _friendSettingsFeedOverride is not null ? await _friendSettingsFeedOverride(imported.Channel) : await _feedClient.GetChannelAsync(imported.Channel, _accountLifetime.Token);
            if (channel is null) throw new FriendCopyException(() => T("Не удалось получить выпуск патча.", "The patch release is unavailable."));
            if (imported.RoamingSpawnMode == "x2" && !SupportsX2(channel))
                throw new FriendCopyException(() => T("В доступном выпуске патча пока нет частоты ×2. Ваши настройки не изменены.", "The available patch release does not include ×2 yet. Your settings were not changed."));
            try { FriendConfiguration.ValidateFeed(imported, channel); }
            catch (InvalidDataException) { throw new FriendCopyException(() => T("Этот выпуск патча не поддерживает настройки друга. Ваши настройки не изменены.", "This patch release does not support your friend's settings. Your settings were not changed.")); }
            // Freeze gameplay options; keep this device's paths, language and personal preferences.
            var snapshot = JsonSerializer.Deserialize<UserSettings>(JsonSerializer.Serialize(_settings))!;
            ConfigurationCode.Apply(imported, snapshot);
            snapshot.PinnedRelease = snapshot.PreparedChannel = snapshot.PreparedFeedFingerprint = null;
            await Revalidate();
            if (_friendSettingsApplyOverride is not null) await _friendSettingsApplyOverride(channel, snapshot, Revalidate);
            else await ApplyConfigurationSnapshotAsync(channel, false, snapshot, Revalidate);
            // The install transaction succeeded. Only now persist the new selection.
            try { RestoreSettings(snapshot, null); }
            catch (Exception error) { ActivityStore.Log(error); throw new FriendCopyException(() => T("Настройки применены к игре, но не удалось сохранить выбор в лаунчере.", "Settings were applied to the game, but the launcher could not save the selection.")); }
            finally { _channel = channel; _latestChannel = channel; }
            succeeded = true;
            CloseSocialDetails(); ApplyLanguage();
            ShowToast(() => T("Конфигурация друга применена.", "Friend's configuration applied."));
            _socialPresenceNext = default;
        }
        catch (FriendCopyException error) { ShowResult(error.LocalizedMessage, failure: true); }
        catch (Exception error) { ShowError(error); }
        finally
        {
            if (localizationChanged is not null) { ConfirmationLocalizationToggle.Checked -= localizationChanged; ConfirmationLocalizationToggle.Unchecked -= localizationChanged; }
            if (receipt is not null) await FinishOfferApplicationAsync(receipt, succeeded);
            SetBusy(false); RefreshStatus();
        }
    }
}
