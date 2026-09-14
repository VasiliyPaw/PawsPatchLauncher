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
    private string? _socialDetailsRoleKey;
    private int _socialDetailsGeneration;
    // Deterministic smoke-test seams; normal runtime uses authenticated RPCs and the transactional installer.
    private Func<Task<IReadOnlyList<SocialPlayer>>>? _friendSettingsReadOverride = null;
    private Func<string, Task<ChannelManifest?>>? _friendSettingsFeedOverride = null;
    private Func<ChannelManifest, UserSettings, Func<Task>, Task>? _friendSettingsApplyOverride = null;

    private void CloseSocialDetails()
    {
        CloseGameActivity();
        _socialDetailsGeneration++;
        Motion.Collapse(SocialDetailsOverlay);
        SocialDetailsCard.IsHitTestVisible=true;
        _socialDetailsPeer = null; _socialDetailsLayoutKey = null;
        _socialDetailsRoleKey = null; SocialDetailsAdminBadge.Content = null;
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
        SocialDetailsCard.IsHitTestVisible=false;
        if(await Motion.HideAsync(SocialDetailsOverlay) && generation==_socialDetailsGeneration)CloseSocialDetails();
    }

    private void ShowSocialDetails(SocialPlayer player)
    {
        if (player.Deleted || (player.Relation != "friend" || !_socialPlayers.Any(p => p.Id == player.Id && p.Relation == "friend"))&& !(_account.AdminLevel>0&&_adminViewedPlayer?.Id==player.Id)) return;
        _socialDetailsGeneration++;
        _socialDetailsPeer = player.Id; RenderSocialDetails(player);
        SocialDetailsCard.IsHitTestVisible=true;
        SocialDetailsOverlay.Visibility = Visibility.Visible;
        SocialDetailsOverlay.UpdateLayout(); Motion.Reveal(SocialDetailsOverlay);
        RevealDialogCard(SocialDetailsCard);
        SocialDetailsClose.Focus();
    }

    private void RenderSocialDetails(SocialPlayer player)
    {
        SocialDetailsName.Text = player.Name;
        var roleKey = $"{player.Id}|{player.Deleted}|{player.AdminLevel}|{player.PawsTeam}|{_text.Language}";
        if (_socialDetailsRoleKey != roleKey)
        {
            _socialDetailsRoleKey = roleKey;
            SocialDetailsAdminBadge.Content = player.Deleted ? null : PlayerRoleBadge(player.AdminLevel,player.PawsTeam,inline:false);
        }
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
        var activity=presence=="playing" ? player.Activity : null;
        SocialDetailsGameActivityRow.Visibility=activity is null ? Visibility.Collapsed : Visibility.Visible;
        SocialDetailsGameActivityText.Text=activity is null ? "" : GameActivityPhaseName(activity.Phase);
        SocialDetailsGameActivityButton.Content=T("Подробнее", "Details");
        SocialDetailsGameActivityButton.ToolTip=T("Состояние игры и участники", "Game activity and participants");
        SocialDetailsGameActivityButton.IsEnabled=!AccountConnectionBlocked;
        SocialDetailsChannelLabel.Text = T("Мод и канал патча", "Mod and patch channel");
        SocialDetailsChannel.Text = player.Channel == "beta" ? T("Бета", "Beta") : player.Channel == "stable" ? T("Релиз", "Release") : T("Неизвестен", "Unknown");
        if (FriendConfiguration.TryParse(player.Configuration,player.Channel,out var gameSettings))
            SocialDetailsChannel.Text = GameMod.Name(gameSettings.Mod, _text.Language == "ru") + " · " + SocialDetailsChannel.Text;
        SocialDetailsComponentsLabel.Text = T(player.Presence == "offline" ? "ПОСЛЕДНИЕ НАСТРОЙКИ" : "КОМПОНЕНТЫ", player.Presence == "offline" ? "LAST KNOWN SETTINGS" : "COMPONENTS");
        SocialDetailsCopyButton.Content = T("Скопировать конфигурацию", "Copy configuration");
        SocialDetailsRelationshipText.Text = T("Чат без добавления в друзья", "Chat without a friendship");
        SocialDetailsRelationshipText.Visibility = !player.IsFriend && !player.Deleted ? Visibility.Visible : Visibility.Collapsed;
        SocialDetailsRemoveButton.Content = player.IsFriend ? T("Удалить из друзей", "Remove friend") : T("Не в друзьях", "Not a friend");
        LauncherIcon.SetKind(SocialDetailsRemoveButton, player.IsFriend ? IconKind.Trash : IconKind.Person);
        SocialDetailsRemoveButton.ToolTip = !player.IsFriend
            ? T("Этот игрок не добавлен в друзья. Чат доступен через функции администрации.", "This player is not on your friends list. This chat is available through administrator features.") : null;
        ToolTipService.SetShowOnDisabled(SocialDetailsRemoveButton, true);
        System.Windows.Automation.AutomationProperties.SetHelpText(SocialDetailsRemoveButton, SocialDetailsRemoveButton.ToolTip?.ToString() ?? "");
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
            var values = exact ? FriendConfiguration.Components(settings) : data.RootElement.EnumerateObject()
                .Where(p => p.Value.ValueKind is JsonValueKind.True or JsonValueKind.False).ToDictionary(p => p.Name, p => p.Value.GetBoolean());
            // Use the actual Components tab labels and its visual order, not JSON property order.
            foreach (var (name, title) in new[] {
                ("core", CoreTitleText), ("colors", ColorsTitleText),
                ("desync", OosTitleText), ("hostility", IndependentTitleText), ("roaming", RoamingSpawnTitleText),
                ("additional_roaming", AdditionalRoamingTitleText), ("siege", SiegeBalanceTitleText),
                ("powers_shards", PowersShardsTitleText) })
            {
                if (!values.TryGetValue(name, out var enabled)) continue;
                var label = name == "core" ? T("Павс патч", "Paw's Patch") : title.Text;
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
        _ = RefreshPeerVersionsAsync(player);
        SocialDetailsComponents.Visibility=SocialDetailsChannel.Visibility=SocialDetailsChannelLabel.Visibility=SocialDetailsComponentsLabel.Visibility=player.Available?Visibility.Visible:Visibility.Collapsed;
    }

    private void RefreshSocialCopyAvailability()
    {
        var player = _socialPlayers.FirstOrDefault(p => p.Id == _socialDetailsPeer && p.Relation == "friend");
        var exact = player is not null && FriendConfiguration.TryParse(player.Configuration, player.Channel, out _);
        var available = player?.Available == true && !_account.Restricted;
        var versionStatus=player is null?PeerVersionStatus.Unknown:FriendVersionStatus(player);
        var hint = !available ? "" : !exact ? T("Игроку нужно открыть новую версию лаунчера с установленным патчем.", "The player needs to open the new launcher with the patch installed.")
            : versionStatus!=PeerVersionStatus.Current ? FriendVersionWarning(versionStatus)
            : _game is null ? T("Сначала выберите папку игры.", "Select the game folder first.")
            : IsGameRunning() ? T("Закройте игру, чтобы применить настройки.", "Close the game to apply settings.")
            : _account.State != AccountState.SignedIn ? T("Для копирования нужно подключение к аккаунту.", "Connect to your account to copy settings.") : "";
        var matches = available && exact && ConfigurationMatches(player!.Configuration);
        SocialDetailsCopyHint.Text = hint.Length == 0 && matches
            ? T("Настройки совпадают. При копировании проверим обновление нужного мода.", "Settings match. Copying will check for an update to the required mod.") : hint;
        SocialDetailsCopyButton.Visibility = available ? Visibility.Visible : Visibility.Collapsed;
        SocialDetailsCopyHint.Visibility = SocialDetailsCopyHint.Text.Length == 0 ? Visibility.Collapsed : Visibility.Visible;
        SocialDetailsCopyHint.Foreground=SocialBrush(versionStatus is not (PeerVersionStatus.Current or PeerVersionStatus.Checking)?"#FFB1A8":"#A8BBD2");
        SocialDetailsCopyButton.ToolTip=hint.Length==0?null:hint;
        ToolTipService.SetShowOnDisabled(SocialDetailsCopyButton,true);
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
        var game = _game;
        var originalCode = player.Configuration;
        OfferReceipt? receipt = null; var succeeded = false; var ownsOperation = false;
        Task<bool>? confirmation = null;
        using var preparationCancellation = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);
        void CheckContext()
        {
            if (_account.UserId != owner || _account.State != AccountState.SignedIn) throw new AccountException("session_expired");
            if (_game?.Directory != game.Directory)
                throw new FriendCopyException(() => T("Папка игры изменилась. Откройте профиль и повторите.", "The game folder changed. Open the profile and try again."));
            EnsureGameClosed();
            var versionStatus=FriendVersionStatus(player);
            if(versionStatus is not (PeerVersionStatus.Current or PeerVersionStatus.Checking))
                throw new FriendCopyException(()=>FriendVersionWarning(versionStatus));
        }
        try
        {
            CheckContext();
            if(offer is not null && ConfigurationMatches(originalCode)) return;
            var baseline=LocalAppliedConfiguration();
            imported = FriendConfiguration.WithLocalLanguages(imported, baseline);
            // Freeze the intended options before checking the destination release.
            var snapshot = JsonSerializer.Deserialize<UserSettings>(JsonSerializer.Serialize(_settings))!;
            ConfigurationCode.Apply(imported, snapshot);
            snapshot.PinnedRelease = snapshot.PreparedChannel = snapshot.PreparedFeedFingerprint = null;
            EnsureModAccess(snapshot.Mod);
            confirmation = ConfirmActionAsync(T("Применить конфигурацию игрока?", "Apply player's configuration?"),
                T("Проверяем доступный выпуск и сохранённые файлы нужного мода…", "Checking the available release and the required mod's saved files…"),
                T("ЧТО ИЗМЕНИТСЯ", "WHAT WILL CHANGE"), "", T("Проверяем…", "Checking…"));
            if (confirmation.IsCompleted) return;
            ConfirmationDeleteButton.IsEnabled = false;
            RenderConfigurationChanges(baseline,imported);
            LauncherIcon.SetKind(ConfirmationDeleteButton, IconKind.Copy); ConfirmationActionIcon.Kind = IconKind.Copy;
            ConfirmationIconBadge.Background = SocialBrush("#403A28"); ConfirmationIconBadge.BorderBrush = SocialBrush("#80662F");
            ConfirmationActionIcon.Foreground = SocialBrush("#E8C879");
            ConfirmationDeleteButton.Background = SocialBrush("#80662F"); ConfirmationDeleteButton.BorderBrush = SocialBrush("#D5AE52");
            Motion.SetHoverBackground(ConfirmationDeleteButton, SocialBrush("#A3833D")); Motion.SetPressedBackground(ConfirmationDeleteButton, SocialBrush("#695425"));
            preparationCancellation.CancelAfter(TimeSpan.FromSeconds(12));
            var preparation = PrepareFriendCopyAsync(snapshot, game, player, preparationCancellation.Token);
            if (await Task.WhenAny(preparation, confirmation) == confirmation)
            {
                preparationCancellation.Cancel();
                // Observe a late failure without touching a newer dialog or operation.
                _ = preparation.ContinueWith(t => { _ = t.Exception; }, TaskContinuationOptions.OnlyOnFaulted);
                return;
            }
            var (channel, plan) = await preparation;
            if (_confirmation?.Task != confirmation || _confirmationFinishing) { await confirmation; return; }
            CheckContext();
            RenderFriendCopyPlan(channel, snapshot, plan);
            if (!await confirmation) return;
            CheckContext();
            CloseSocialDetails();
            ownsOperation = true;
            SetBusy(true, T("Применяю конфигурацию…", "Applying configuration…"));
            ShowToast(() => T("Началось применение конфигурации друга.", "Applying your friend's configuration."));
            if (offer is not null) receipt = await BeginOfferApplicationAsync(offer);
            async Task Revalidate()
            {
                CheckContext();
                var friends = _friendSettingsReadOverride is not null ? await _friendSettingsReadOverride() : await _account.GetFriendsAsync(_accountLifetime.Token);
                CheckContext();
                var fresh = friends.FirstOrDefault(p => p.Id == player.Id && p.Relation == "friend");
                if (fresh is null || offer is null && (fresh.Configuration != originalCode || fresh.Channel != player.Channel))
                    throw new FriendCopyException(() => T("Данные друга изменились. Откройте профиль и повторите.", "Your friend's details changed. Open their profile and try again."));
                RequireCurrentPeerVersions(fresh with {Configuration=originalCode,Channel=player.Channel},_friendVersionCatalogs[channel.Channel]);
                if (receipt is not null) await VerifyOfferApplicationAsync(receipt);
                EnsureGameClosed();
            }
            await Revalidate();
            // Apply exactly the signed release shown in the confirmation.
            await ValidateFriendCopyGameAsync(channel, snapshot, game, _accountLifetime.Token);
            await Revalidate();
            if (_friendSettingsApplyOverride is not null) await _friendSettingsApplyOverride(channel, snapshot, Revalidate);
            else await ApplyConfigurationSnapshotAsync(channel, true, snapshot, Revalidate, requireExactConfiguration: true);
            // The install transaction succeeded. Only now persist the new selection.
            try { RestoreSettings(snapshot, null); }
            catch (Exception error) { ActivityStore.Log(error); throw new FriendCopyException(() => T("Настройки применены к игре, но не удалось сохранить выбор в лаунчере.", "Settings were applied to the game, but the launcher could not save the selection.")); }
            finally { _channel = channel; _latestChannel = channel; _offeredModChannel = channel; }
            succeeded = true;
            CloseSocialDetails(); ApplyLanguage();
            ShowToast(() => T("Конфигурация друга применена.", "Friend's configuration applied."));
            _socialPresenceNext = default;
        }
        catch (Exception error)
        {
            var cancelled = !ownsOperation && confirmation is not null
                && (_confirmation?.Task != confirmation || _confirmationFinishing);
            if (confirmation is not null && _confirmation?.Task == confirmation) await CompleteConfirmationAsync(false);
            if (!cancelled)
            {
                if (error is FriendCopyException friendError) ShowResult(friendError.LocalizedMessage, failure: true);
                else if (error is OperationCanceledException) ShowResult(() => T("Не удалось завершить проверку. Проверьте подключение и повторите. Настройки не изменены.", "The check could not finish. Check your connection and try again. Settings were not changed."), failure: true);
                else ShowError(error);
            }
        }
        finally
        {
            preparationCancellation.Cancel();
            if (receipt is not null) await FinishOfferApplicationAsync(receipt, succeeded);
            if (ownsOperation) { SetBusy(false); RefreshStatus(); }
        }
    }
}
