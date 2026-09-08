using System.ComponentModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Media.Animation;
using XamlAnimatedGif;

namespace PawsPatchLauncher;
public partial class MainWindow
{
    private ChatMedia? _chatMedia;
    private string? _mediaOwner;
    private CancellationTokenSource _mediaRender=new();
    private readonly List<Action> _mediaCleanup=[];
    private int _mediaBudget;
    private void ResetChatMedia(bool dispose=false)
    {
        _mediaRender.Cancel();_mediaRender.Dispose();_mediaRender=new();_mediaBudget=16;
        foreach(var clean in _mediaCleanup)clean();_mediaCleanup.Clear();
        if(dispose||_mediaOwner!=_account.UserId){_chatMedia?.Dispose();_chatMedia=null;_mediaOwner=_account.UserId;}
    }
    private ContextMenu CreateChatMediaMenu(FrameworkElement anchor,Uri uri,CancellationToken token)
    {
        var menu=new ContextMenu {Style=(Style)FindResource("SocialContextMenu"),PlacementTarget=anchor,Placement=PlacementMode.MousePoint,StaysOpen=false};
        var copy=new MenuItem {Tag="copy_media_link",Header=T("Скопировать ссылку","Copy link"),Style=(Style)FindResource("SocialMenuItem"),
            Foreground=SocialBrush("#EDF0F5"),Icon=new LauncherIcon {Kind=IconKind.Copy,Width=19,Height=19,Foreground=SocialBrush("#EDF0F5")}};
        copy.Click+=async(_,e)=>{
            e.Handled=true;CloseSocialMenu();
            if(!token.IsCancellationRequested)await CopyTextAsync(uri.OriginalString,()=>T("Ссылка скопирована.","Link copied."));
        };
        menu.Items.Add(copy);
        menu.Opened+=(_,_)=>{if(menu.Template.FindName("MenuSurface",menu) is FrameworkElement surface)Motion.Reveal(surface);};
        menu.Closed+=(_,_)=>{if(ReferenceEquals(_socialMenu,menu))_socialMenu=null;};
        return menu;
    }
    private void AddChatMedia(StackPanel content,string body)
    {
        var bodyText=content.Children.OfType<TextBlock>().FirstOrDefault(t=>t.Tag as string=="message-body");
        var loaded=new HashSet<string>(StringComparer.Ordinal);
        void RefreshBody()
        {
            if(bodyText is null)return;
            bodyText.Text=ChatMedia.WithoutLoadedLinks(body,loaded);
            bodyText.Visibility=string.IsNullOrWhiteSpace(bodyText.Text)?Visibility.Collapsed:Visibility.Visible;
        }
        foreach(var uri in ChatMedia.Find(body))
        {
            if(_mediaBudget--<=0)return;
            var host=new Border {Margin=new Thickness(0,9,0,0),CornerRadius=new CornerRadius(6),Background=SocialBrush("#0E2033"),Padding=new Thickness(3),HorizontalAlignment=HorizontalAlignment.Left};
            var load=new Button {Style=(Style)FindResource("GhostButton"),Content=T("Показать изображение · ","Load image · ")+uri.IdnHost,HorizontalAlignment=HorizontalAlignment.Left};
            host.Child=load;content.Children.Add(host);
            var token=_mediaRender.Token;bool started=false;Action? releaseCurrent=null;
            void LinkVisible(bool visible)
            {
                if(visible?loaded.Remove(uri.AbsoluteUri):loaded.Add(uri.AbsoluteUri))RefreshBody();
            }
            void Failed(bool gif=false)
            {
                if(token.IsCancellationRequested)return;
                LinkVisible(true);host.Child=load;
                releaseCurrent?.Invoke();releaseCurrent=null;
                load.IsEnabled=true;started=false;
                load.Content=gif?T("Не удалось показать GIF · повторить","Could not display GIF · retry"):T("Не удалось загрузить · повторить","Could not load · retry");
            }
            host.MouseRightButtonUp+=(_,e)=>{
                if(host.Child is not Image {Source:not null}||token.IsCancellationRequested||ConfirmationActive)return;
                e.Handled=true;CloseSocialMenu();
                RevealSocialMenu(CreateChatMediaMenu(host,uri,token));
            };
            async Task Load()
            {
                if(started||token.IsCancellationRequested)return;
                started=true;load.IsEnabled=false;load.Content=T("Загрузка…","Loading…");
                try
                {
                    var bytes=await (_chatMedia??=new ChatMedia()).LoadAsync(uri,token);token.ThrowIfCancellationRequested();
                    using var dimensions=new MemoryStream(bytes,false);
                    var decoder=BitmapDecoder.Create(dimensions,BitmapCreateOptions.DelayCreation,BitmapCacheOption.None);
                    var frame=decoder.Frames[0];ChatMedia.CheckDimensions(frame.PixelWidth,frame.PixelHeight);
                    var picture=new Image {MaxHeight=280,MaxWidth=420,Stretch=Stretch.Uniform,HorizontalAlignment=HorizontalAlignment.Left,ToolTip=T("ПКМ — скопировать ссылку","Right-click to copy link")};
                    host.Child=picture;
                    var property=DependencyPropertyDescriptor.FromProperty(Image.SourceProperty,typeof(Image));
                    EventHandler sourceChanged=(_,_)=>{
                        if(!token.IsCancellationRequested&&ReferenceEquals(host.Child,picture))LinkVisible(picture.Source is null);
                    };
                    property.AddValueChanged(picture,sourceChanged);
                    MemoryStream? stream=null;bool released=false;
                    void Release()
                    {
                        if(released)return;released=true;
                        property.RemoveValueChanged(picture,sourceChanged);
                        AnimationBehavior.SetSourceStream(picture,null);picture.Source=null;stream?.Dispose();
                    }
                    releaseCurrent=Release;_mediaCleanup.Add(Release);
                    if(ChatMedia.IsGif(bytes))
                    {
                        AnimationBehavior.AddErrorHandler(picture,(_,e)=>{
                            e.Handled=true;
                            if(ReferenceEquals(host.Child,picture))Failed(true);
                        });
                        stream=new MemoryStream(bytes,false);
                        AnimationBehavior.SetRepeatBehavior(picture,RepeatBehavior.Forever);
                        AnimationBehavior.SetSourceStream(picture,stream);
                    }
                    else
                    {
                        using var data=new MemoryStream(bytes,false);
                        var bitmap=new BitmapImage();bitmap.BeginInit();bitmap.CacheOption=BitmapCacheOption.OnLoad;bitmap.DecodePixelWidth=Math.Min(840,frame.PixelWidth);
                        bitmap.StreamSource=data;bitmap.EndInit();bitmap.Freeze();picture.Source=bitmap;
                    }
                }
                catch(OperationCanceledException) when(!token.IsCancellationRequested){Failed();}
                catch(OperationCanceledException){}
                catch {Failed();}
            }
            load.Click+=async(_,_)=>await Load();
            if(ChatMedia.Automatic(uri)&&!ActivityStore.IsSmokeTest)host.Loaded+=async(_,_)=>{if(host.IsVisible)await Load();};
        }
    }
}
