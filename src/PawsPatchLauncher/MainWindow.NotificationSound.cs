using Microsoft.Win32;
using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly NotificationAudio _notificationAudio = new();
    private string? _soundOwner;
    private bool _volumeReady;
    private IReadOnlyList<SocialPlayer> _soundPlayers = [];
    private string NotificationSoundPath => Path.Combine(ActivityStore.Root, "notification.wav");
    private void InitializeNotificationSound() => Closed += (_,_) => _notificationAudio.Dispose();
    private void ApplyNotificationSoundLanguage()
    {
        FriendsComposerMoreButton.ToolTip=T("Предложения и сохранения", "Offers and saves");
        System.Windows.Automation.AutomationProperties.SetName(FriendsComposerMoreButton,FriendsComposerMoreButton.ToolTip.ToString());
        NotificationSoundToggle.Content = T("Звук сообщений и заявок", "Message and request sound");
        NotificationSoundToggle.IsChecked = _settings.NotificationSoundEnabled;
        NotificationSoundNameText.Text = string.IsNullOrEmpty(_settings.NotificationSoundName) ? T("Мягкий щипок · стандартный", "Soft pluck · default") : _settings.NotificationSoundName;
        NotificationSoundChooseButton.Content = T("Выбрать WAV", "Choose WAV");
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
    private void NotificationSoundChoose_Click(object sender,RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Filter="WAV (*.wav)|*.wav", Title=T("Звук уведомления", "Notification sound"), CheckFileExists=true };
        if (dialog.ShowDialog(this) != true) return;
        try
        {
            using var file = new FileStream(dialog.FileName,FileMode.Open,FileAccess.Read,FileShare.Read);
            if (file.Length > NotificationAudio.MaximumBytes) throw new InvalidDataException();
            var bytes = new byte[(int)file.Length]; file.ReadExactly(bytes); NotificationAudio.Validate(bytes);
            Directory.CreateDirectory(ActivityStore.Root);
            File.WriteAllBytes(NotificationSoundPath+".tmp",bytes); File.Move(NotificationSoundPath+".tmp",NotificationSoundPath,true);
            _settings.NotificationSoundName=Path.GetFileName(dialog.FileName); _settingsStore.Save(_settings); ApplyNotificationSoundLanguage();
            PlayNotificationSound(preview:true);
        }
        catch { ShowToast(()=>T("Выберите PCM WAV до 2 МБ и 15 секунд.", "Choose a PCM WAV up to 2 MB and 15 seconds."),true); }
    }
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
