namespace PawsPatchLauncher;

public partial class MainWindow
{
    private async Task<(ChannelManifest Channel, FriendCopyPlan Plan)> PrepareFriendCopyAsync(UserSettings selection,
        GameInstallation game, SocialPlayer player, CancellationToken token)
    {
        var channel = _friendSettingsFeedOverride is not null
            ? await _friendSettingsFeedOverride(selection.Channel).WaitAsync(token)
            : await _feedClient.GetChannelAsync(selection.Channel, token);
        token.ThrowIfCancellationRequested();
        if (channel is null || channel.Channel != selection.Channel)
            throw new FriendCopyException(() => T("Не удалось получить выпуск патча.", "The patch release is unavailable."));
        var launcher=await ReadLatestFriendLauncherAsync(token);
        channel=_feedClient.KnownChannel(selection.Channel)??channel;
        RequireCurrentPeerVersions(player,ObserveFriendVersionCatalog(channel,launcher));
        if (GameMod.IsArcaneWars(selection) && selection.RoamingSpawnMode == "x2" && !SupportsX2(channel))
            throw new FriendCopyException(() => T("В доступном выпуске патча пока нет частоты ×2. Ваши настройки не изменены.", "The available patch release does not include ×2 yet. Your settings were not changed."));
        try { FriendConfiguration.ValidateFeed(selection, channel); }
        catch (InvalidDataException)
        {
            throw new FriendCopyException(() => T("Этот выпуск патча не поддерживает настройки игрока. Ваши настройки не изменены.", "This patch release does not support the player's settings. Your settings were not changed."));
        }
        await ValidateFriendCopyGameAsync(channel, selection, game, token);
        var plan = await Task.Run(() =>
        {
            token.ThrowIfCancellationRequested();
            var installer = new ModuleInstaller(game.Directory);
            return FriendCopyPlan.Create(channel, selection, new ModLibrary(game.Directory).Find(selection.Mod, selection.Channel),
                package => { token.ThrowIfCancellationRequested(); return LocallyAvailable(installer, package); });
        }, token);
        return (channel, plan);
    }

    private async Task ValidateFriendCopyGameAsync(ChannelManifest channel, UserSettings selection, GameInstallation game, CancellationToken token)
    {
        if (_friendSettingsApplyOverride is null && GameMod.UsesExecutableFeatures(selection, channel))
        {
            var requirement = GameMod.Requirement(channel, selection.Mod);
            if (requirement.K2ExeSha256.Count > 0 && !GameCompatibilityPolicy.Supports(requirement, await CryptoAndIO.Sha256Async(game.ExecutablePath, token)))
                throw new FriendCopyException(() => T("Версия вашей игры не поддерживает полный набор игрока. Выберите доступные файловые компоненты вручную.", "Your game version does not support the player's full configuration. Select available file components manually."));
        }
    }

    private void RenderFriendCopyPlan(ChannelManifest channel, UserSettings selection, FriendCopyPlan plan)
    {
        var mod = GameMod.Name(selection.Mod, _text.Language == "ru");
        var modVersion = channel.Packages.FirstOrDefault(p => p.Id == selection.Mod)?.Version;
        var patchVersion = GameMod.PawPatchSelected(selection) ? PawPatchVersions.ForChannel(channel, selection.Mod) : null;
        var release = mod + (string.IsNullOrWhiteSpace(modVersion) ? "" : " " + modVersion)
            + " · " + (selection.Channel == "beta" ? T("Бета", "Beta") : T("Релиз", "Release"));
        if (!string.IsNullOrWhiteSpace(patchVersion)) release += "\nPaw’s Patch " + patchVersion;
        var description = plan.Action switch
        {
            FriendCopyAction.Install when plan.Repair => T("Часть сохранённых файлов отсутствует. Лаунчер восстановит их и применит настройки игрока.", "Some saved files are missing. The launcher will restore them and apply the player's settings."),
            FriendCopyAction.Install => T("Этот мод с компонентами патча ещё не установлен в выбранном канале. Лаунчер установит его и применит настройки игрока.", "This mod and its patch components are not installed in the selected channel. The launcher will install them and apply the player's settings."),
            FriendCopyAction.Update => T("Сохранённый выпуск отличается от доступного. Лаунчер обновит этот мод и его компоненты патча, затем применит настройки игрока.", "The saved release differs from the available release. The launcher will update this mod and its patch components, then apply the player's settings."),
            _ => T("Нужный мод и компоненты патча уже сохранены. Лаунчер применит настройки игрока.", "The required mod and patch components are already saved. The launcher will apply the player's settings.")
        };
        if (plan.DownloadCount > 0) description += " " + T("Недостающие файлы будут скачаны.", "Missing files will be downloaded.");
        else description += " " + T("Повторное скачивание не требуется.", "No additional download is needed.");
        ConfirmationBodyText.Text = release + "\n\n" + description + "\n\n"
            + T("Версии лаунчера и патча игрока проверены. Языки текста и озвучки, сохранения и другие установленные моды останутся на месте.",
                "The player's launcher and patch versions have been checked. Your text and speech languages, saves and other installed mods will be kept.");
        ConfirmationDeleteButton.Content = plan.Action switch
        {
            FriendCopyAction.Install => T("Установить и применить", "Install and apply"),
            FriendCopyAction.Update => T("Обновить и применить", "Update and apply"),
            _ => T("Применить", "Apply")
        };
        ConfirmationDeleteButton.IsEnabled = true;
    }
}
