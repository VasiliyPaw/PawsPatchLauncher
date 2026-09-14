namespace PawsPatchLauncher;

public partial class MainWindow
{
    private void RefreshInstalledPatchVersions(InstallState? state)
    {
        ChannelManifest? installed = null;
        if (state?.ReleaseId is { Length: 64 } release)
            try { installed = _feedClient.LoadArchived(release, state.AppliedSettings?.Channel ?? "stable"); }
            catch { /* The installed package still supplies the legacy/offline version. */ }
        var version = PawPatchVersions.Installed(state, installed);
        var core = PawPatchVersions.InstalledCore(state);
        PatchVersionText.Text = version ?? "-";
        var mod = InstalledModVersions.Mod(state) ?? (_game is not null ? GameMod.Vanilla : null);
        var modVersion = mod is null ? null : InstalledModVersions.Version(mod, state, installed, _installedGameVersion);
        InstalledPatchText.Text = mod is null ? T("Не установлено", "Not installed")
            : GameMod.Name(mod) + " " + (modVersion ?? "—") + (version is null ? "" : "\nPaw's Patch " + version);
        InstalledPatchText.ToolTip = mod is null ? null : InstalledPatchText.Text
            + (version is null ? "" : " · " + (state?.AppliedSettings?.Channel == "beta" ? T("Бета", "Beta") : T("Релиз", "Release")))
            + (modVersion is null ? T("\nВерсия игры или мода не определена.", "\nThe game or mod version is unknown.") : "");
        PatchDownloadedText.Text = version is not null ? core?.DownloadedAt is DateTimeOffset downloaded
            ? T("Скачана: ", "Downloaded: ") + downloaded.ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
            : T("Дата загрузки неизвестна", "Download date unavailable") : "";
    }
}
