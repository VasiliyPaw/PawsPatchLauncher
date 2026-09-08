using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly ChatActivityOrder _chatActivity=new();
    private readonly Dictionary<Guid,(StackPanel Row,Button Open,string Signature,bool Selected)> _chatRows=[];
    private ChatListMotion? _chatListMotion;
    private string? _chatRowsOwner,_chatRowsScope;

    private void ObserveChatMessage(Guid owner,SocialMessage message)
    {
        if(_account.UserId!=owner.ToString())return;
        _chatActivity.SetOwner(_account.UserId);
        var peer=message.SenderId==owner?message.RecipientId:message.SenderId;
        _chatActivity.Observe(peer,message.CreatedAt,message.Ordinal);
    }
    private async Task OpenChatByIdAsync(Guid id)
    {
        var player=_socialPlayers.FirstOrDefault(p=>p.Id==id&&p.Relation=="friend");
        if(player is not null)await OpenSocialChatAsync(player);
    }
}
