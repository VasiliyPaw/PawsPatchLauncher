namespace PawsPatchLauncher;

public partial class MainWindow
{
    private void RefreshInstalledPatchVersions(InstallState? state)
    {
        ChannelManifest? installed = null;
        if (state?.AppliedSettings?.Mod is GameMod.Vanilla or GameMod.Immortals && state.ReleaseId is { Length: 64 } release)
            try { installed = _feedClient.LoadArchived(release, state.AppliedSettings.Channel); }
            catch { /* The installed package still supplies the legacy/offline version. */ }
        var version = PawPatchVersions.Installed(state, installed);
        var core = PawPatchVersions.InstalledCore(state);
        PatchVersionText.Text = version ?? "-";
        InstalledPatchText.Text = version is not null ? version + " · " +
            (state?.AppliedSettings?.Channel == "beta" ? T("Бета", "Beta") : T("Релиз", "Release")) : T("Не установлен", "Not installed");
        PatchDownloadedText.Text = version is not null ? core?.DownloadedAt is DateTimeOffset downloaded
            ? T("Скачана: ", "Downloaded: ") + downloaded.ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
            : T("Дата загрузки неизвестна", "Download date unavailable") : "";
        if (version is null && state?.AppliedSettings is { } applied)
            InstalledPatchText.Text = GameMod.Name(applied.Mod, _text.Language == "ru");
        else if (version is null && state?.Modules.ContainsKey("arcane-wars") == true)
            InstalledPatchText.Text = "Arcane Wars";
    }
}
