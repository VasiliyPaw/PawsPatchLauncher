namespace PawsPatchLauncher;
public partial class MainWindow
{
    private readonly Dictionary<Guid,SocialOffer> _sendingOffers=[];
    private UserSettings LocalAppliedConfiguration()=>_game is null?_settings:new ModuleInstaller(_game.Directory).LoadState()?.AppliedSettings??_settings;
    private bool ConfigurationMatches(string? code)
    {
        if(string.IsNullOrEmpty(code))return false;
        try{code=ConfigurationCode.Create(ConfigurationCode.Parse(code));}catch{return false;}
        return code==ConfigurationCode.Create(LocalAppliedConfiguration());
    }
    private bool CanAcceptOffer(SocialOffer offer)=>!_busy&&!ConfirmationActive&&!_account.Restricted
        && _socialPlayers.FirstOrDefault(p=>p.Id==offer.Sender)?.Available!=false
        && (offer.Kind!="config"||!IsGameRunning()&&!ConfigurationMatches(offer.Configuration));
    private async Task CancelSocialOfferAsync(SocialOffer offer)
    {
        if(_busy||ConfirmationActive||offer.Sender.ToString()!=_account.UserId)return;
        try{UpdateLocalOffer(await _account.OfferActionAsync(offer.Id,"cancel",ct:_accountLifetime.Token));}
        catch(AccountException e){HandleEndedAccount(e.Code);ShowToast(()=>SocialError(e.Code),true);}
        catch(OperationCanceledException){}
        catch{ShowToast(()=>T("Не удалось отменить предложение. Повторите попытку.","Could not cancel the offer. Please retry."),true);}
    }
}
