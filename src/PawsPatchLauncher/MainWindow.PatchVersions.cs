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
        var mod = state?.AppliedSettings?.Mod ?? (state?.Modules.ContainsKey("immortals") == true ? GameMod.Immortals : GameMod.ArcaneWars);
        InstalledPatchText.Text = version is not null ? GameMod.Name(mod) + "\nPaw's Patch " + version : T("Не установлено", "Not installed");
        InstalledPatchText.ToolTip = version is not null ? InstalledPatchText.Text + " · " +
            (state?.AppliedSettings?.Channel == "beta" ? T("Бета", "Beta") : T("Релиз", "Release")) : null;
        PatchDownloadedText.Text = version is not null ? core?.DownloadedAt is DateTimeOffset downloaded
            ? T("Скачана: ", "Downloaded: ") + downloaded.ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
            : T("Дата загрузки неизвестна", "Download date unavailable") : "";
        if (version is null && state?.AppliedSettings is { } applied)
            InstalledPatchText.Text = GameMod.Name(applied.Mod, _text.Language == "ru");
        else if (version is null && state?.Modules.ContainsKey("arcane-wars") == true)
            InstalledPatchText.Text = "Arcane Wars";
    }
}
