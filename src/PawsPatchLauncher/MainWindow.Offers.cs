using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using Microsoft.Win32;

namespace PawsPatchLauncher;
public partial class MainWindow
{
    private IReadOnlyList<SocialOffer> _socialOffers=[];
    private OfferReceipt? _offerApplying;
    private bool _offerSending,_offerPulseBusy;
    private DateTimeOffset _offerNextPulse;
    private OfferReceiptStore OfferReceipts => new(ActivityStore.Root);
    private async Task<OfferReceipt> BeginOfferApplicationAsync(SocialOffer offer)
    {
        if(!Guid.TryParse(_account.UserId,out var owner)||owner!=offer.Recipient)throw new AccountException("session_expired");
        var attempt=Guid.NewGuid();
        var fresh=await _account.OfferActionAsync(offer.Id,"begin",attempt,_accountLifetime.Token);
        if(_account.UserId!=owner.ToString())throw new AccountException("session_expired");
        if(fresh.State!="applying"||fresh.Attempt!=attempt)throw new AccountException("offer_unavailable");
        var receipt=new OfferReceipt(owner,offer.Id,attempt);
        // Persist an interrupted fallback before any local game/save mutation.
        OfferReceipts.Save(receipt);_offerApplying=receipt;UpdateLocalOffer(fresh);
        return receipt;
    }
    private async Task VerifyOfferApplicationAsync(OfferReceipt receipt)
    {
        if(_account.UserId!=receipt.Owner.ToString())throw new AccountException("session_expired");
        var fresh=await _account.OfferActionAsync(receipt.Offer,"touch",receipt.Attempt,_accountLifetime.Token);
        if(_account.UserId!=receipt.Owner.ToString())throw new AccountException("session_expired");
        if(fresh.State!="applying"||fresh.Attempt!=receipt.Attempt)throw new AccountException("offer_unavailable");
    }
    private async Task FinishOfferApplicationAsync(OfferReceipt receipt,bool succeeded)
    {
        try { OfferReceipts.Save(receipt with { Completed=succeeded }); }
        catch { ShowToast(()=>T("Не удалось сохранить результат передачи. Проверьте состояние предложения после подключения.", "Could not save the transfer result. Check the offer after reconnecting."),true); }
        finally { _offerApplying=null; }
        await PulseOffersAsync(force:true);
    }
    private void UpdateLocalOffer(SocialOffer offer)
    {
        if(_account.UserId!=offer.Sender.ToString()&&_account.UserId!=offer.Recipient.ToString())return;
        _sendingOffers.Remove(offer.Id);
        _socialOffers=_socialOffers.Where(o=>o.Id!=offer.Id).Append(offer).ToArray();RenderSocialMessages();
    }
    private async Task PulseOffersAsync(bool force=false)
    {
        if(ActivityStore.IsSmokeTest||_offerPulseBusy||!force&&DateTimeOffset.UtcNow<_offerNextPulse||!Guid.TryParse(_account.UserId,out var owner))return;
        _offerPulseBusy=true;_offerNextPulse=DateTimeOffset.UtcNow.AddSeconds(20);
        try
        {
            if(_offerApplying is OfferReceipt active) await VerifyOfferApplicationAsync(active);
            foreach(var receipt in OfferReceipts.Read(owner).Where(r=>r.Offer!=_offerApplying?.Offer))
            {
                if(_account.UserId!=owner.ToString())return;
                try
                {
                    var fresh=await _account.OfferActionAsync(receipt.Offer,receipt.Completed?"complete":"fail",receipt.Attempt,_accountLifetime.Token);
                    OfferReceipts.Remove(receipt);
                    if(_account.UserId==owner.ToString())UpdateLocalOffer(fresh);
                }
                catch(AccountException e) when(e.Code is "offer_unavailable" or "friend_required" or "offer_expired") { OfferReceipts.Remove(receipt); }
            }
        }
        catch(AccountException e){HandleEndedAccount(e.Code);}
        catch(OperationCanceledException){}
        catch { /* Durable receipts remain for the next authenticated reconnect. */ }
        finally{_offerPulseBusy=false;}
    }
    private async void FriendsComposerMore_Click(object sender,RoutedEventArgs e)
    {
        if(_offerSending||_busy||_accountBusy||_socialPeer is null||_account.State!=AccountState.SignedIn)return;
        CloseSocialMenu();
        var menu=new ContextMenu { Style=(Style)FindResource("SocialContextMenu"),PlacementTarget=(Button)sender,Placement=PlacementMode.Top,HorizontalOffset=-180,VerticalOffset=-6 };
        foreach(var config in new[]{true,false})
        {
            var item=new MenuItem { Header=config?T("Предложить конфигурацию","Offer configuration"):T("Отправить сейв","Send save"),Style=(Style)FindResource("SocialMenuItem"),
                Icon=new LauncherIcon{Kind=config?IconKind.Copy:IconKind.Save,Width=19,Height=19,Foreground=SocialBrush("#EDF0F5")} };
            item.Click+=async (_,_)=>{CloseSocialMenu();await SendSocialOfferAsync(config);};menu.Items.Add(item);
        }
        _socialMenu=menu;menu.IsOpen=true;await Task.CompletedTask;
    }
    private async Task SendSocialOfferAsync(bool config)
    {
        if(_offerSending||_busy||FeedBlocksActions||_accountBusy||ConfirmationActive||_socialPeer is not Guid peer||!Guid.TryParse(_account.UserId,out var owner)||!_socialPlayers.Any(p=>p.Id==peer&&p.Relation=="friend"))return;
        _offerSending=true;RenderSocialIdentity();
        try
        {
            string? code=null;SaveTransferDescriptor? descriptor=null;byte[]? bytes=null;
            if(config)
            {
                var state=_game is null?null:new ModuleInstaller(_game.Directory).LoadState();
                if(state?.AppliedSettings is not UserSettings applied||!state.Modules.TryGetValue("pawpatch-core",out var core)||!core.Enabled)
                    throw new FriendCopyException(()=>T("Сначала установите и примените конфигурацию патча.", "Install and apply the patch configuration first."));
                code=ConfigurationCode.Create(applied);
                var friends=_friendSettingsReadOverride is not null?await _friendSettingsReadOverride():await _account.GetFriendsAsync(_accountLifetime.Token);
                if(_account.UserId!=owner.ToString()||_socialPeer!=peer)return;
                var recipient=friends.FirstOrDefault(p=>p.Id==peer&&p.Relation=="friend");
                if(recipient is null)throw new AccountException("friend_required");
                if(!await ConfirmConfigurationOfferAsync(recipient,code))return;
            }
            else
            {
                var picker=new OpenFileDialog{Title=T("Выберите сохранение","Choose a save"),Filter="Kohan II (*.rsg)|*.rsg",InitialDirectory=SavesDirectory,CheckFileExists=true};
                if(picker.ShowDialog(this)!=true)return;
                using var file=new FileStream(picker.FileName,FileMode.Open,FileAccess.Read,FileShare.Read);
                if(file.Length>SaveTransferGuard.MaximumBytes)throw new InvalidDataException();
                bytes=new byte[(int)file.Length];await file.ReadExactlyAsync(bytes,_accountLifetime.Token);
                descriptor=SaveTransferGuard.Describe(Path.GetFileName(picker.FileName),bytes);
                await _account.CleanupTransfersAsync(_accountLifetime.Token);
            }
            if(_account.UserId!=owner.ToString()||_socialPeer!=peer)return;
            await DeliverPreparedOfferAsync(owner,peer,code,descriptor,bytes,_accountLifetime.Token);
            if(_account.UserId!=owner.ToString())return;
            await LoadSocialChatAsync(owner);ShowNewestCachedHistory();
        }
        catch(FriendCopyException e){ShowToast(e.LocalizedMessage,true);}
        catch(AccountException e){HandleEndedAccount(e.Code);ShowToast(()=>SocialError(e.Code),true);}
        catch(InvalidDataException){ShowToast(()=>T("Нужен корректный сейв Kohan II (.rsg), не больше 20 МБ.", "Choose a valid Kohan II .rsg save up to 20 MB."),true);}
        catch(OperationCanceledException){}
        catch { ShowToast(()=>T("Не удалось отправить предложение. Повторите отправку.", "Could not send the offer. Try again."),true); }
        finally{
            _offerSending=false;RenderSocialIdentity();RenderSocialMessages();
        }
    }

    private async Task DeliverPreparedOfferAsync(Guid owner, Guid peer, string? code,
        SaveTransferDescriptor? descriptor, byte[]? bytes, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        if (_account.UserId != owner.ToString()) throw new OperationCanceledException();
        var key = OfferSendIdentity.Key(owner,peer,code??descriptor!.FileName+"|"+descriptor.Sha256);
        var id = OfferSendIdentity.Get(ActivityStore.Root,key);
        var now = DateTimeOffset.UtcNow;
        _sendingOffers[id] = new SocialOffer(id,owner,peer,code is not null?"config":"save",code,descriptor?.FileName,
            descriptor?.Size,descriptor?.Sha256,"sending",now,now.AddMinutes(10),null,null);
        RenderSocialRows();
        RenderSocialMessages();
        if (_socialPeer == peer) ShowNewestCachedHistory();
        var sent = false;
        try
        {
            var offer = await _account.CreateOfferAsync(peer,id,code,descriptor,ct);
            if(_account.UserId==owner.ToString() && _sendingOffers.TryGetValue(id,out var prepared))
                _sendingOffers[id]=prepared with {CreatedAt=offer.CreatedAt};
            if (offer.State == "expired") { OfferSendIdentity.Complete(ActivityStore.Root,key); throw new AccountException("offer_expired"); }
            if (bytes is not null && offer.State is "uploading" or "pending")
                await _account.TransferSaveAsync(id,"upload",bytes,ct);
            OfferSendIdentity.Complete(ActivityStore.Root,key);
            sent = true;
            if(_account.UserId==owner.ToString()) { _chatActivity.SetOwner(_account.UserId);_chatActivity.Observe(peer,offer.CreatedAt); }
        }
        finally
        {
            // Retain the same durable identity after any uncertain network outcome.
            if (_account.UserId == owner.ToString() && _sendingOffers.TryGetValue(id,out var local))
                _sendingOffers[id] = local with { State=sent?"pending":"send_failed" };
            RenderSocialRows(); RenderSocialMessages();
        }
    }
    private async Task<bool> ConfirmConfigurationOfferAsync(SocialPlayer recipient,string code)
    {
        if(ConfirmationActive||_busy||FeedBlocksActions)return false;
        var known=FriendConfiguration.TryParse(recipient.Configuration,recipient.Channel,out var theirs);
        var ours=ConfigurationCode.Parse(code);
        var matches=known&&ConfigurationCode.Create(theirs)==ConfigurationCode.Create(ours);
        var details=recipient.Name+" · @"+AccountService.NormalizeUsername(recipient.Nickname)+"\n\n";
        details+=!known?T("Нет данных о конфигурации друга. Попросите его открыть лаунчер с установленным патчем.",
            "Your friend's configuration is unavailable. Ask them to open the launcher with the patch installed.")
            :matches?T("Ваши конфигурации уже совпадают. Отправка не требуется.","Your configurations already match. There is nothing to send.")
            :string.Join("\n",ConfigurationChanges.Describe(theirs,ours,_text.Language=="ru"));
        var confirmation=ConfirmActionAsync(T("Предложить конфигурацию?","Offer configuration?"),
            T("Друг получит предложение и сам решит, применять ли изменения.","Your friend will receive an offer and choose whether to apply the changes."),
            T("ИЗМЕНЕНИЯ У ДРУГА","CHANGES FOR YOUR FRIEND"),details,T("Отправить предложение","Send offer"));
        ConfirmationDeleteButton.IsEnabled=known&&!matches;
        if(known&&!matches)RenderConfigurationChanges(theirs,ours,recipient.Name+" · @"+AccountService.NormalizeUsername(recipient.Nickname));
        LauncherIcon.SetKind(ConfirmationDeleteButton,IconKind.Copy);ConfirmationActionIcon.Kind=IconKind.Copy;
        ConfirmationDeleteButton.Background=SocialBrush("#80662F");ConfirmationDeleteButton.BorderBrush=SocialBrush("#D5AE52");
        Motion.SetHoverBackground(ConfirmationDeleteButton,SocialBrush("#A3833D"));Motion.SetPressedBackground(ConfirmationDeleteButton,SocialBrush("#695425"));
        return await confirmation&&known&&!matches;
    }

    private string OfferStateText(SocialOffer offer)
    {
        var own=offer.Sender.ToString()==_account.UserId;
        return offer.State switch {
            "pending"=>offer.Kind=="config" ? T(own?"Предложение конфигурации отправлено":"Вам предлагают скопировать конфигурацию",own?"Configuration offer sent":"You've been offered a configuration")
                :T(own?"Сохранение отправлено":"Вам предлагают сохранение",own?"Save sent":"You've been sent a save"),
            "applying"=>T(offer.Kind=="config"?"Конфигурация применяется…":"Сохранение загружается…",offer.Kind=="config"?"Applying configuration…":"Downloading save…"),
            "accepted"=>T(offer.Kind=="config"?"Конфигурация принята и применена":"Сохранение принято",offer.Kind=="config"?"Configuration accepted and applied":"Save accepted"),
            "sending"=>T(offer.Kind=="save"?"Загрузка сохранения…":"Отправка предложения…",offer.Kind=="save"?"Uploading save…":"Sending offer…"),
            "send_failed"=>T("Не удалось отправить. Повторите отправку через меню.", "Could not send. Retry from the menu."),
            "cancelled"=>T("Предложение отменено отправителем","Offer cancelled by sender"),
            "declined"=>T("Предложение отклонено","Offer declined"),
            "expired"=>T("Время ожидания истекло · 10 минут","Offer expired · 10 minutes"),
            "failed"=>T(offer.Kind=="config"?"Применение конфигурации прервано":"Передача сохранения прервана",offer.Kind=="config"?"Configuration application interrupted":"Save transfer interrupted"),
            _=>T("Подготовка…","Preparing…")
        };
    }
    private FrameworkElement RenderOfferCard(SocialOffer offer)
    {
        var content=new StackPanel();
        var header=new DockPanel();
        var time=new TextBlock {Tag="offer-time",Text=ChatTime(offer.CreatedAt),ToolTip=ChatDate(offer.CreatedAt),FontSize=11,
            Foreground=SocialBrush("#A8BBD2"),VerticalAlignment=VerticalAlignment.Center,Margin=new Thickness(12,0,0,0)};
        DockPanel.SetDock(time,Dock.Right);header.Children.Add(time);
        header.Children.Add(new LauncherIcon{Kind=offer.Kind=="config"?IconKind.Copy:IconKind.Save,Width=22,Height=22,Margin=new Thickness(0,0,10,0),Foreground=SocialBrush("#E4C777")});
        var author=_socialPlayers.FirstOrDefault(p=>p.Id==offer.Sender);
        var authorName=new WrapPanel();authorName.Children.Add(new TextBlock{Text=author is null?_account.DisplayName:PlayerDisplayName(author),FontSize=12,Foreground=SocialBrush("#A8BBD2"),VerticalAlignment=VerticalAlignment.Center});
        var level=offer.Sender.ToString()==_account.UserId?_account.AdminLevel:author?.AdminLevel??0;if(level>0&&author?.Deleted!=true)authorName.Children.Add(AdministratorBadge(level));header.Children.Add(authorName);
        content.Children.Add(header);
        content.Children.Add(new TextBlock{Text=OfferStateText(offer),TextWrapping=TextWrapping.Wrap,FontWeight=FontWeights.SemiBold,Margin=new Thickness(0,10,0,0),
            Foreground=SocialBrush(offer.State=="accepted"?"#76DAB0":offer.State=="failed"?"#EF9E98":"#EDF0F5")});
        if(offer.Kind=="save")content.Children.Add(new TextBlock{Text=offer.FileName+" · "+FormatBytes(offer.FileSize??0),TextWrapping=TextWrapping.Wrap,Foreground=SocialBrush("#A8BBD2"),Margin=new Thickness(0,7,0,0)});
        if(offer.State=="pending"&&offer.Recipient.ToString()==_account.UserId)
        {
            var actions=new WrapPanel{Margin=new Thickness(0,12,0,0)};
            var accept=SocialButton(T("Принять","Accept"),()=>AcceptSocialOfferAsync(offer));accept.Style=(Style)FindResource("GoldButton");
            var decline=SocialButton(T("Отклонить","Decline"),async()=>{
                if(_busy||ConfirmationActive)return;
                try{UpdateLocalOffer(await _account.OfferActionAsync(offer.Id,"decline",ct:_accountLifetime.Token));}
                catch(AccountException e){ShowToast(()=>SocialError(e.Code),true);}
                catch(OperationCanceledException){}
                catch{ShowToast(()=>T("Не удалось отклонить предложение. Повторите попытку.","Could not decline the offer. Try again."),true);}
            });
            accept.Tag=offer.Kind=="config"?offer.Configuration:null;
            accept.IsEnabled=CanAcceptOffer(offer);decline.IsEnabled=!_busy&&!ConfirmationActive;actions.Children.Add(accept);actions.Children.Add(decline);content.Children.Add(actions);
        }
        if(offer.Sender.ToString()==_account.UserId && offer.State is "pending" or "uploading"){
            var actions=new WrapPanel{Margin=new Thickness(0,12,0,0)};
            actions.Children.Add(SocialButton(T("Отменить предложение","Cancel offer"),()=>CancelSocialOfferAsync(offer)));
            content.Children.Add(actions);
        }
        return new Border { Opacity=offer.State=="sending"?.55:1,Tag=offer.Id,Background=SocialBrush("#172B41"),BorderBrush=SocialBrush("#4C657E"),BorderThickness=new Thickness(1),CornerRadius=new CornerRadius(9),Padding=new Thickness(14),Margin=new Thickness(8,0,8,12),Child=content };
    }
    private void RefreshOfferActions()
    {
        foreach(var card in FriendsMessagesPanel.Children.OfType<Border>())
            if(card.Child is StackPanel panel)
                foreach(var actions in panel.Children.OfType<WrapPanel>())
                    foreach(var button in actions.Children.OfType<Button>())
                        button.IsEnabled=!_busy&&!ConfirmationActive&&!_account.Restricted&&SocialContactAvailable(_socialPlayers.FirstOrDefault(p=>p.Id==_socialPeer)) && (button.Tag is not string code || !IsGameRunning()&&!ConfigurationMatches(code));
    }
    private async Task AcceptSocialOfferAsync(SocialOffer offer)
    {
        if(!CanAcceptOffer(offer)||_account.UserId!=offer.Recipient.ToString()||offer.State!="pending")return;
        if(_socialPlayers.FirstOrDefault(p=>p.Id==offer.Sender&&p.Relation=="friend"&&p.Available) is not SocialPlayer friend)return;
        if(offer.Kind=="config")await CopyConfigurationAsync(friend with {Configuration=offer.Configuration,Channel=offer.Channel},offer);
        else await AcceptSaveOfferAsync(offer);
    }
    private async Task AcceptSaveOfferAsync(SocialOffer offer)
    {
        OfferReceipt? receipt=null;var succeeded=false;var owner=_account.UserId;
        try
        {
            offer.Validate(Guid.Parse(owner));var directory=SavesDirectory;
            var path=Path.Combine(directory,offer.FileName!);string? existing=null;
            if(File.Exists(path))
            {
                existing=await CryptoAndIO.Sha256Async(path);
                if(!await ConfirmActionAsync(T("Заменить сохранение?","Replace this save?"),
                    T("Текущее сохранение будет сохранено в резервной копии.", "The existing save will be backed up."),
                    T("СОХРАНЕНИЕ","SAVE"),offer.FileName!,T("Принять и заменить","Accept and replace")))return;
            }
            if(_account.UserId!=owner)return;
            SetBusy(true,T("Получаю сохранение…","Receiving save…"));
            receipt=await BeginOfferApplicationAsync(offer);
            var bytes=await _account.TransferSaveAsync(offer.Id,"download",ct:_accountLifetime.Token);
            SaveTransferGuard.ValidateBytes(offer.Save,bytes);await VerifyOfferApplicationAsync(receipt);
            await SaveTransferGuard.InstallAsync(directory,offer.Save,bytes,existing,IsGameRunning,_accountLifetime.Token,allowWhileRunning:true);
            succeeded=true;ShowToast(()=>T("Сохранение принято.", "Save received."));
        }
        catch(AccountException e){HandleEndedAccount(e.Code);ShowToast(()=>SocialError(e.Code),true);}
        catch(IOException){ShowToast(()=>T("Сейв сейчас занят или изменился. Повторите получение после завершения записи.", "The save is busy or changed. Retry after the write finishes."),true);}
        catch(Exception e){ShowError(e);}
        finally{if(receipt is not null)await FinishOfferApplicationAsync(receipt,succeeded);SetBusy(false);RefreshStatus();}
    }
}
