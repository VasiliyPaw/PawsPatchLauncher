using Microsoft.Win32;
using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly NotificationAudio _notificationAudio = new();
    private string? _soundOwner;
    private bool _volumeReady;
    private bool _soundImportBusy;
    private readonly CancellationTokenSource _soundImportLifetime = new();
    private IReadOnlyList<SocialPlayer> _soundPlayers = [];
    private string NotificationSoundPath => Path.Combine(ActivityStore.Root, "notification.wav");
    private void InitializeNotificationSound() => Closed += (_,_) => { _soundImportLifetime.Cancel(); _notificationAudio.Dispose(); };
    private void ApplyNotificationSoundLanguage()
    {
        FriendsComposerMoreButton.ToolTip=T("Предложения и сохранения", "Offers and saves");
        System.Windows.Automation.AutomationProperties.SetName(FriendsComposerMoreButton,FriendsComposerMoreButton.ToolTip.ToString());
        NotificationSoundToggle.Content = T("Звук сообщений и заявок", "Message and request sound");
        NotificationSoundToggle.IsChecked = _settings.NotificationSoundEnabled;
        NotificationSoundNameText.Text = string.IsNullOrEmpty(_settings.NotificationSoundName) ? T("Мягкий щипок · стандартный", "Soft pluck · default") : _settings.NotificationSoundName;
        NotificationSoundChooseButton.Content = _soundImportBusy ? T("Обработка…", "Processing…") : T("Выбрать звук", "Choose sound");
        NotificationSoundChooseButton.ToolTip = T("WAV, MP3, OGG, Opus, FLAC, M4A, AAC, WMA, AIFF · до 20 МБ и 15 секунд", "WAV, MP3, OGG, Opus, FLAC, M4A, AAC, WMA, AIFF · up to 20 MB and 15 seconds");
        NotificationSoundChooseButton.IsEnabled = NotificationSoundResetButton.IsEnabled = NotificationSoundPreviewButton.IsEnabled = !_soundImportBusy;
        NotificationSoundPreviewButton.Content = T("Прослушать", "Preview");
        NotificationSoundResetButton.Content = T("По умолчанию", "Reset");
        _volumeReady=false;
        NotificationVolumeLabel.Text=T("Громкость", "Volume");
        NotificationVolumeSlider.Value=Math.Clamp(_settings.NotificationVolume,0,100);
        NotificationVolumeValue.Text=$"{NotificationVolumeSlider.Value:0}%";
        _volumeReady=true;
    }
    private void NotificationVolume_Changed(object sender,RoutedPropertyChangedEventArgs<double> e)
    {
        if(!_volumeReady)return;
        _settings.NotificationVolume=(int)e.NewValue;NotificationVolumeValue.Text=$"{e.NewValue:0}%";
        _settingsStore.Save(_settings);
    }
    private void NotificationSoundToggle_Click(object sender,RoutedEventArgs e)
    { _settings.NotificationSoundEnabled = NotificationSoundToggle.IsChecked == true; _settingsStore.Save(_settings); }
    private async void NotificationSoundChoose_Click(object sender,RoutedEventArgs e)
    {
        if (_soundImportBusy) return;
        var dialog = new OpenFileDialog { Filter=T("Звуковые файлы", "Audio files")+"|"+NotificationSoundImporter.Extensions+"|"+T("Все файлы", "All files")+"|*.*", Title=T("Звук уведомления", "Notification sound"), CheckFileExists=true };
        if (dialog.ShowDialog(this) != true) return;
        await ImportNotificationSoundAsync(dialog.FileName);
    }
    private async Task ImportNotificationSoundAsync(string path)
    {
        if (_soundImportBusy) return;
        _soundImportBusy=true; ApplyNotificationSoundLanguage();
        try
        {
            var bytes = await Task.Run(()=>NotificationSoundImporter.Import(path,_soundImportLifetime.Token),_soundImportLifetime.Token);
            _soundImportLifetime.Token.ThrowIfCancellationRequested();
            Directory.CreateDirectory(ActivityStore.Root);
            File.WriteAllBytes(NotificationSoundPath+".tmp",bytes); File.Move(NotificationSoundPath+".tmp",NotificationSoundPath,true);
            _settings.NotificationSoundName=Path.GetFileName(path); _settingsStore.Save(_settings);
            PlayNotificationSound(preview:true);
        }
        catch (OperationCanceledException) when (_soundImportLifetime.IsCancellationRequested) { }
        catch (SoundImportException error) { ShowToast(()=>SoundImportMessage(error.Reason),true); }
        catch { ShowToast(()=>T("Не удалось прочитать или сохранить звук. Проверьте доступ к файлу.", "Could not read or save the sound. Check file access."),true); }
        finally { _soundImportBusy=false; ApplyNotificationSoundLanguage(); }
    }
    private string SoundImportMessage(SoundImportError reason) => reason switch
    {
        SoundImportError.TooLarge => T("Выберите звук размером до 20 МБ.", "Choose a sound up to 20 MB."),
        SoundImportError.TooLong => T("Звук длиннее 15 секунд. Выберите более короткий фрагмент.", "The sound is longer than 15 seconds. Choose a shorter clip."),
        SoundImportError.Unsupported => T("Этот формат звука не поддерживается. Выберите WAV, MP3, OGG, Opus, FLAC, M4A, AAC, WMA или AIFF.", "This audio format is not supported. Choose WAV, MP3, OGG, Opus, FLAC, M4A, AAC, WMA or AIFF."),
        _ => T("Не удалось прочитать звук: файл повреждён или для него нет подходящего аудиокодека.", "Could not read the sound: the file is damaged or an audio codec is unavailable.")
    };
    private void NotificationSoundReset_Click(object sender,RoutedEventArgs e)
    { _settings.NotificationSoundName=""; _settingsStore.Save(_settings); ApplyNotificationSoundLanguage(); }
    private void NotificationSoundPreview_Click(object sender,RoutedEventArgs e) => PlayNotificationSound(preview:true);
    private void PlayNotificationSound(bool preview=false)
    {
        if (ActivityStore.IsSmokeTest || !preview && !_settings.NotificationSoundEnabled) return;
        try
        {
            var bytes = _settings.NotificationSoundName.Length>0 && File.Exists(NotificationSoundPath) && new FileInfo(NotificationSoundPath).Length<=NotificationAudio.MaximumBytes
                ? File.ReadAllBytes(NotificationSoundPath) : NotificationAudio.DefaultBytes();
            _notificationAudio.Play(bytes,_settings.NotificationVolume/100d);
        }
        catch { if (preview) ShowToast(()=>T("Не удалось воспроизвести звук.", "Could not play the sound."),true); }
    }
    private void NotifySocialArrival(Guid owner,IReadOnlyList<SocialPlayer> players)
    {
        // First snapshot is a baseline, not a burst of old notifications. Counts can go down on reads.
        if (_soundOwner==owner.ToString() && NotificationAudio.HasNewArrival(_soundPlayers,players))
            PlayNotificationSound();
        _soundOwner=owner.ToString(); _soundPlayers=players;
    }
}
