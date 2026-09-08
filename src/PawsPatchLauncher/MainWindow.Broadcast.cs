using Microsoft.Win32;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    // Match the server's separate per-kind minute limits; other storage/active caps still apply.
    private int BroadcastLimit => _broadcastConfig ? 5 : 10;
    private sealed record BroadcastEntry(SocialPlayer Player, CheckBox Select, TextBlock Status)
    {
        public bool Sent { get; set; }
    }
    private readonly List<BroadcastEntry> _broadcastEntries = [];
    private string? _broadcastOwner, _broadcastCode;
    private byte[]? _broadcastBytes;
    private SaveTransferDescriptor? _broadcastSave;
    private bool _broadcastConfig, _broadcastRunning, _broadcastClosing;
    private CancellationTokenSource? _broadcastCancellation;
    private int _broadcastGeneration;
    private bool _broadcastCloseAfterSend, _broadcastPicking;
    private sealed record PreparedBroadcastSave(SaveTransferDescriptor Descriptor, byte[] Bytes);
    private Func<Task<string?>>? _broadcastPickPathOverride = null;
    private Func<Guid,Guid,string?,SaveTransferDescriptor?,byte[]?,CancellationToken,Task>? _broadcastSendOverride = null;

    private void ResetBroadcast()
    {
        _broadcastGeneration++;
        _broadcastCancellation?.Cancel();
        _broadcastOwner = null;
        _broadcastCloseAfterSend=false;
        _broadcastBytes = null; _broadcastSave = null; _broadcastCode = null;
        _broadcastEntries.Clear(); BroadcastRows.Children.Clear();
        Motion.Collapse(BroadcastOverlay);
    }

    private async void FriendsBroadcast_Click(object sender, RoutedEventArgs e) => await OpenBroadcastFlowAsync(false);
    private async void SendSaveBroadcast_Click(object sender, RoutedEventArgs e) => await OpenBroadcastFlowAsync(true);
    private async Task OpenBroadcastFlowAsync(bool quickSave)
    {
        if (_offerSending || _busy || _accountBusy || ConfirmationActive || _account.State != AccountState.SignedIn) return;
        var owner = _account.UserId;
        _offerSending = true; RenderSocialIdentity();
        try
        {
            var prepared = quickSave ? await PickBroadcastSaveAsync() : null;
            if (quickSave && prepared is null || _account.UserId != owner) return;
            var friends = _friendSettingsReadOverride is not null ? await _friendSettingsReadOverride()
                : await _account.GetFriendsAsync(_accountLifetime.Token);
            if (_account.UserId != owner) return;
            OpenBroadcast(owner!, friends);
            _broadcastCloseAfterSend=quickSave;
            if(prepared is not null)
            {
                _broadcastBytes=prepared.Bytes; _broadcastSave=prepared.Descriptor;
                RefreshBroadcastKind();
            }
        }
        catch (AccountException error) { HandleEndedAccount(error.Code); ShowToast(()=>SocialError(error.Code),true); }
        catch (OperationCanceledException) { }
        catch { ShowToast(()=>T("Не удалось загрузить друзей.", "Could not load friends."),true); }
        finally { _offerSending=false; RenderSocialIdentity(); }
    }

    private void OpenBroadcast(string owner, IReadOnlyList<SocialPlayer> friends)
    {
        ResetBroadcast(); CloseSocialMenu();
        _broadcastOwner=owner; _broadcastClosing=false; _broadcastConfig=false;
        var state=_game is null?null:new ModuleInstaller(_game.Directory).LoadState();
        if (state?.AppliedSettings is UserSettings applied && state.Modules.GetValueOrDefault("pawpatch-core")?.Enabled==true)
            _broadcastCode=ConfigurationCode.Create(applied);
        BroadcastTitle.Text=T("Отправить друзьям","Send to friends");
        BroadcastConfigTab.Content=T("Конфигурация","Configuration");
        BroadcastSaveTab.Content=T("Сейв","Save");
        BroadcastChooseFile.Content=T("Выбрать сейв…","Choose save…");
        foreach (var player in friends.Where(p=>p.Relation=="friend").OrderBy(p=>p.Name,StringComparer.CurrentCultureIgnoreCase))
        {
            var status=new TextBlock {FontSize=11,Foreground=SocialBrush("#9EB5CE"),TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,5,0,0)};
            var select=new CheckBox {Style=(Style)FindResource("BroadcastRecipient"),Margin=new Thickness(0,0,0,8)};
            var content=new DockPanel();
            var avatar=SocialAvatar(player.Id,36,false); avatar.Margin=new Thickness(0,0,12,0); DockPanel.SetDock(avatar,Dock.Left);
            content.Children.Add(avatar);
            var names=new StackPanel(); names.Children.Add(SocialNameLabel(player)); names.Children.Add(status); content.Children.Add(names);
            select.Content=content;
            System.Windows.Automation.AutomationProperties.SetName(select,player.Name+" @"+player.Nickname);
            _broadcastEntries.Add(new BroadcastEntry(player,select,status));
            select.Checked+=(_,_)=>RefreshBroadcastSelection(); select.Unchecked+=(_,_)=>RefreshBroadcastSelection();
            BroadcastRows.Children.Add(select);
        }
        if (_broadcastEntries.Count == 0) BroadcastHint.Text=T("Друзей пока нет","No friends yet");
        RefreshBroadcastKind();
        Motion.Reveal(BroadcastOverlay); BroadcastSaveTab.Focus();
    }

    private string? BroadcastIneligible(SocialPlayer friend)
    {
        if(!friend.Available||_account.Restricted)return T("Общение недоступно","Contact unavailable");
        if (!_broadcastConfig) return _broadcastSave is null ? T("Выберите сейв","Choose a save") : null;
        if (_broadcastCode is null) return T("Патч ещё не установлен","Patch not installed yet");
        if (!FriendConfiguration.TryParse(friend.Configuration,friend.Channel,out var theirs))
            return T("Конфигурация друга неизвестна","Friend's configuration unavailable");
        return ConfigurationCode.Create(theirs)==_broadcastCode ? T("Конфигурации совпадают","Configurations already match") : null;
    }

    private void RefreshBroadcastKind()
    {
        BroadcastHint.Text=string.Format(T("Выберите до {0} друзей. Каждый получит отдельное предложение в чате.",
            "Select up to {0} friends. Each receives an individual offer in chat."),BroadcastLimit);
        SetNavState(BroadcastConfigTab,_broadcastConfig); SetNavState(BroadcastSaveTab,!_broadcastConfig);
        BroadcastChooseFile.Visibility=_broadcastConfig?Visibility.Collapsed:Visibility.Visible;
        BroadcastPayloadText.Text=_broadcastConfig
            ? _broadcastCode is null ? T("Сначала установите и примените патч.","Install and apply the patch first.")
                : T("Ваша установленная конфигурация","Your installed configuration")+" · "+
                    (ConfigurationCode.Parse(_broadcastCode).Channel=="beta"?T("Бета","Beta"):T("Релиз","Release"))
            : _broadcastSave is null ? T("Один выбранный файл для всех получателей.","One selected file for all recipients.")
                : _broadcastSave.FileName+" · "+FormatBytes(_broadcastSave.Size);
        foreach(var entry in _broadcastEntries)
        {
            entry.Select.IsChecked=false; entry.Sent=false;
            var reason=BroadcastIneligible(entry.Player);
            entry.Status.Text=reason??T("Готово к отправке","Ready to send");
            entry.Status.Foreground=SocialBrush(reason is null?"#9EB5CE":"#D5AE52");
            entry.Select.ToolTip=_broadcastConfig && reason is null
                ? string.Join("\n",ConfigurationChanges.Describe(ConfigurationCode.Parse(entry.Player.Configuration!),ConfigurationCode.Parse(_broadcastCode!),_text.Language=="ru")) : reason;
        }
        RefreshBroadcastSelection();
    }

    private void RefreshBroadcastSelection()
    {
        var count=_broadcastEntries.Count(e=>e.Select.IsChecked==true&&!e.Sent);
        foreach(var entry in _broadcastEntries)
            entry.Select.IsEnabled=!_broadcastRunning&&!entry.Sent&&BroadcastIneligible(entry.Player) is null
                && (count<BroadcastLimit||entry.Select.IsChecked==true);
        BroadcastConfigTab.IsEnabled=BroadcastSaveTab.IsEnabled=BroadcastChooseFile.IsEnabled=!_broadcastRunning&&!_broadcastPicking;
        BroadcastSendButton.IsEnabled=!_broadcastRunning&&!_broadcastPicking&&count>0&&count<=BroadcastLimit;
        BroadcastSendButton.Content=_broadcastRunning?T("Отправка…","Sending…"):T("Отправить","Send")+(count>0?" · "+count:"");
        if(!_broadcastRunning) BroadcastSummary.Text=T("Выбрано: ","Selected: ")+count+" / "+BroadcastLimit+
            (_broadcastEntries.Any(e=>e.Sent) ? " · "+T("Отправлено: ","Sent: ")+_broadcastEntries.Count(e=>e.Sent) : "");
    }

    private void BroadcastKind_Click(object sender,RoutedEventArgs e)
    {
        if(_broadcastRunning || _broadcastPicking || sender is not Button {Tag:string kind} || _broadcastConfig==(kind=="config"))return;
        _broadcastConfig=kind=="config"; RefreshBroadcastKind();
    }

    private async void BroadcastChooseFile_Click(object sender,RoutedEventArgs e)
    {
        if(_broadcastRunning || _broadcastPicking || _account.UserId!=_broadcastOwner)return;
        var owner=_broadcastOwner; var generation=_broadcastGeneration;
        _broadcastPicking=true; RefreshBroadcastSelection();
        try
        {
            var prepared=await PickBroadcastSaveAsync();
            if(prepared is null || owner!=_account.UserId || generation!=_broadcastGeneration)return;
            _broadcastBytes=prepared.Bytes; _broadcastSave=prepared.Descriptor; RefreshBroadcastKind();
        }
        finally { _broadcastPicking=false; if(generation==_broadcastGeneration)RefreshBroadcastSelection(); }
    }

    private async Task<PreparedBroadcastSave?> PickBroadcastSaveAsync()
    {
        try
        {
            string? path;
            if(_broadcastPickPathOverride is not null)path=await _broadcastPickPathOverride();
            else
            {
                var picker=new OpenFileDialog {Title=T("Выберите сохранение","Choose a save"),Filter="Kohan II (*.rsg)|*.rsg",InitialDirectory=SavesDirectory,CheckFileExists=true};
                path=picker.ShowDialog(this)==true?picker.FileName:null;
            }
            if(path is null)return null;
            using var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);
            if(file.Length>SaveTransferGuard.MaximumBytes)throw new InvalidDataException();
            var bytes=new byte[(int)file.Length]; await file.ReadExactlyAsync(bytes,_accountLifetime.Token);
            return new(SaveTransferGuard.Describe(Path.GetFileName(path),bytes),bytes);
        }
        catch(OperationCanceledException) { }
        catch { ShowToast(()=>T("Нужен корректный сейв Kohan II (.rsg), не больше 20 МБ.","Choose a valid Kohan II .rsg save up to 20 MB."),true); }
        return null;
    }

    private async void BroadcastSend_Click(object sender,RoutedEventArgs e)=>await SendBroadcastAsync();

    private async Task SendBroadcastAsync()
    {
        if(_broadcastRunning||_broadcastPicking||_offerSending||_busy||_accountBusy||FeedBlocksActions||ConfirmationActive
            ||_account.State!=AccountState.SignedIn||_broadcastOwner!=_account.UserId||!Guid.TryParse(_broadcastOwner,out var owner))return;
        var selected=_broadcastEntries.Where(e=>e.Select.IsChecked==true&&!e.Sent&&BroadcastIneligible(e.Player) is null).ToArray();
        if(selected.Length<1||selected.Length>BroadcastLimit)return;
        var code=_broadcastConfig?_broadcastCode:null;
        var bytes=_broadcastConfig?null:_broadcastBytes;
        var save=_broadcastConfig?null:_broadcastSave;
        var generation=_broadcastGeneration;
        using var cancellation=CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);
        _broadcastCancellation=cancellation;
        _broadcastRunning=_offerSending=true; RefreshBroadcastSelection(); RenderSocialIdentity();
        var completed=0;
        try
        {
            var current=_friendSettingsReadOverride is not null?await _friendSettingsReadOverride():await _account.GetFriendsAsync(cancellation.Token);
            cancellation.Token.ThrowIfCancellationRequested();
            if(_account.UserId!=owner.ToString()||generation!=_broadcastGeneration)return;
            if(bytes is not null)await _account.CleanupTransfersAsync(cancellation.Token);
            foreach(var entry in selected)
            {
                cancellation.Token.ThrowIfCancellationRequested();
                if(_account.UserId!=owner.ToString()||generation!=_broadcastGeneration)break;
                var friend=current.FirstOrDefault(p=>p.Id==entry.Player.Id&&p.Relation=="friend");
                var reason=friend is null?T("Больше не в друзьях","No longer a friend"):BroadcastIneligible(friend);
                if(reason is not null){entry.Status.Text=reason;entry.Status.Foreground=SocialBrush("#F3AA96");continue;}
                entry.Status.Text=T("Отправляется…","Sending…");
                BroadcastSummary.Text=T("Отправлено: ","Sent: ")+completed+" / "+selected.Length;
                try
                {
                    if(_broadcastSendOverride is not null)await _broadcastSendOverride(owner,friend!.Id,code,save,bytes,cancellation.Token);
                    else await DeliverPreparedOfferAsync(owner,friend!.Id,code,save,bytes,cancellation.Token);
                    if(_account.UserId!=owner.ToString()||generation!=_broadcastGeneration)break;
                    entry.Sent=true; entry.Select.IsChecked=false; completed++;
                    entry.Status.Text=T("Предложение отправлено","Offer sent"); entry.Status.Foreground=SocialBrush("#76DAB0");
                }
                catch(AccountException error)
                {
                    entry.Status.Text=SocialError(error.Code);entry.Status.Foreground=SocialBrush("#F3AA96");
                    HandleEndedAccount(error.Code);
                    if(error.Code is "rate_limit" or "network" or "outcome_unknown" || _account.UserId!=owner.ToString())break;
                }
                catch(OperationCanceledException){throw;}
                catch {entry.Status.Text=T("Не отправлено — можно повторить","Not sent — you can retry");entry.Status.Foreground=SocialBrush("#F3AA96");}
            }
            if(_account.UserId==owner.ToString()&&generation==_broadcastGeneration)
            {
                var sent=completed;
                ShowToast(()=>T("Предложения отправлены: ","Offers sent: ")+sent+" / "+selected.Length+
                    (sent<selected.Length?T(". Повторите оставшиеся позже.",". Retry the remaining recipients later."):""),sent<selected.Length);
            }
        }
        catch(OperationCanceledException) { }
        catch(AccountException error){HandleEndedAccount(error.Code);ShowToast(()=>SocialError(error.Code),true);}
        catch {ShowToast(()=>T("Отправка прервана. Уже отправленные предложения сохранены.","Sending interrupted. Previously sent offers are preserved."),true);}
        finally
        {
            _broadcastCancellation=null; _broadcastRunning=_offerSending=false;
            if(generation==_broadcastGeneration)
            {
                foreach(var entry in selected.Where(e=>!e.Sent && e.Status.Text==T("Отправляется…","Sending…")))
                    entry.Status.Text=T("Отправка прервана — можно повторить","Sending interrupted — you can retry");
                RefreshBroadcastSelection();
                if(_broadcastClosing || _broadcastCloseAfterSend && completed==selected.Length && !cancellation.IsCancellationRequested)
                    await DismissBroadcastAsync(generation);
            }
            RenderSocialIdentity(); RenderSocialMessages();
        }
    }

    private async void BroadcastClose_Click(object sender,RoutedEventArgs e)=>await CloseBroadcastAsync();
    private async Task CloseBroadcastAsync()
    {
        if(_broadcastRunning){_broadcastClosing=true;_broadcastCancellation?.Cancel();return;}
        await DismissBroadcastAsync(_broadcastGeneration);
    }
    private async Task DismissBroadcastAsync(int generation)
    {
        await Motion.HideAsync(BroadcastOverlay);
        if(generation==_broadcastGeneration && BroadcastOverlay.Visibility!=Visibility.Visible)ResetBroadcast();
    }
    private async void BroadcastOverlay_MouseDown(object sender,MouseButtonEventArgs e)
    {
        if(InsideCard(e.OriginalSource as DependencyObject,BroadcastCard))return;
        e.Handled=true;await CloseBroadcastAsync();
    }
    private async void BroadcastOverlay_KeyDown(object sender,KeyEventArgs e)
    {
        if(e.Key!=Key.Escape)return;
        e.Handled=true;await CloseBroadcastAsync();
    }
}
