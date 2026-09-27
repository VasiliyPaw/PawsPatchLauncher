namespace PawsPatchLauncher;
public partial class MainWindow
{
    private readonly Dictionary<Guid,SocialOffer> _sendingOffers=[];
    // RefreshStatus refreshes this snapshot after discovery/install/repair. A
    // chat repaint must not reparse the multi-megabyte installation journal for
    // every offer button; applying an offer still uses the normal installer checks.
    private UserSettings LocalAppliedConfiguration()=>_game is null?_settings:_friendCopyAppliedState?.AppliedSettings??_settings;
    private bool ConfigurationMatches(string? code)
    {
        if(string.IsNullOrEmpty(code))return false;
        try { return FriendConfiguration.Matches(ConfigurationCode.Parse(code),LocalAppliedConfiguration()); }
        catch { return false; }
    }
    private bool CanAcceptOffer(SocialOffer offer)=>!_busy&&!ConfirmationActive&&!_account.Restricted
        && _socialPlayers.FirstOrDefault(p=>p.Id==offer.Sender)?.Available!=false
        && (offer.Kind!="config"||!IsGameRunning()&&!ConfigurationMatches(offer.Configuration)
            && _socialPlayers.FirstOrDefault(p=>p.Id==offer.Sender) is { } sender
            && FriendVersionStatus(sender with { Configuration=offer.Configuration,Channel=offer.Channel })==PeerVersionStatus.Current);
    private async Task CancelSocialOfferAsync(SocialOffer offer)
    {
        if(_busy||ConfirmationActive||offer.Sender.ToString()!=_account.UserId)return;
        try{UpdateLocalOffer(await _account.OfferActionAsync(offer.Id,"cancel",ct:_accountLifetime.Token));}
        catch(AccountException e){HandleEndedAccount(e.Code);ShowToast(()=>SocialError(e.Code),true);}
        catch(OperationCanceledException){}
        catch{ShowToast(()=>T("Не удалось отменить предложение. Повторите попытку.","Could not cancel the offer. Please retry."),true);}
    }
}
