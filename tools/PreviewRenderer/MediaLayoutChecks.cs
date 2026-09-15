using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class MediaLayoutChecks
{
    internal static void Probe(Uri uri)
    {
        // Explicit read-only diagnostic: public media only, no URL logging or disk cache.
        using var media=new ChatMedia();
        var bytes=Task.Run(()=>media.LoadAsync(uri,CancellationToken.None)).GetAwaiter().GetResult();
        using var stream=new MemoryStream(bytes,false);
        var decoder=BitmapDecoder.Create(stream,BitmapCreateOptions.None,BitmapCacheOption.OnLoad);
        var frame=decoder.Frames[0];ChatMedia.CheckDimensions(frame.PixelWidth,frame.PixelHeight);
        Console.WriteLine($"MEDIA PROBE PASS bytes={bytes.Length} width={frame.PixelWidth} height={frame.PixelHeight} decoder={decoder.GetType().Name}");
    }
    private const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
    private static object Field(MainWindow w,string name)=>typeof(MainWindow).GetField(name,Flags)!.GetValue(w)!;
    private static void Set(MainWindow w,string name,object value)=>typeof(MainWindow).GetField(name,Flags)!.SetValue(w,value);
    private static object? Invoke(MainWindow w,string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,Flags)!.Invoke(w,args);
    internal static void Populate(MainWindow w)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Media layout fixtures require smoke mode.");
        SocialChecks.Populate(w,"chat");
        var owner=Guid.Parse(((AccountService)Field(w,"_account")).UserId);
        var peer=((IReadOnlyList<SocialPlayer>)Field(w,"_socialPlayers")).First(p=>p.Relation=="friend").Id;
        Set(w,"_socialPending",(IReadOnlyList<PendingSocialMessage>)Array.Empty<PendingSocialMessage>());
        Set(w,"_socialMessages",(IReadOnlyList<SocialMessage>)new[]{
            new SocialMessage(owner,Guid.NewGuid(),peer,"https://example.com/wide.png","text",DateTimeOffset.Now.AddMinutes(-2)),
            new SocialMessage(peer,Guid.NewGuid(),owner,"https://example.com/portrait.png","text",DateTimeOffset.Now.AddMinutes(-1))});
        Invoke(w,"RenderSocialMessages");
        Set(w,"_chatMedia",new ChatMedia(new Fixture()));
        foreach(var bubble in Bubbles(w))
            foreach(var media in ((StackPanel)bubble.Child).Children.OfType<Border>())
                ((Button)media.Child).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        var frame=new DispatcherFrame();var timer=new DispatcherTimer {Interval=TimeSpan.FromMilliseconds(150)};
        timer.Tick+=(_,_)=>{timer.Stop();frame.Continue=false;};timer.Start();Dispatcher.PushFrame(frame);
    }
    private static Border[] Bubbles(MainWindow w)=>((StackPanel)w.FindName("FriendsMessagesPanel")).Children.OfType<Grid>().Where(g => g.Tag is Guid).Select(g=>g.Children.OfType<Border>().Single()).ToArray();
    internal static void Run(string language)
    {
        var w=new MainWindow();int checks=0;
        void Check(bool ok,string reason){checks++;if(!ok)throw new Exception("Media layout: "+reason);}
        try
        {
            ((PawsPatchLauncher.Localization)Field(w,"_text")).SetLanguage(language);Invoke(w,"ApplyLanguage");Populate(w);
            var content=(FrameworkElement)w.Content;
            foreach(var size in new[]{new Size(1440,900),new Size(1050,680)})
            {
                content.Measure(size);content.Arrange(new Rect(size));content.UpdateLayout();
                var bubbles=Bubbles(w);
                Check(bubbles[0].HorizontalAlignment==HorizontalAlignment.Right&&bubbles[1].HorizontalAlignment==HorizontalAlignment.Left,"media alignment by sender");
                foreach(var bubble in bubbles)
                {
                    var panel=(StackPanel)bubble.Child;var host=panel.Children.OfType<Border>().Single();var image=(Image)host.Child;
                    Check(image.Source is not null&&image.ActualWidth>0&&image.ActualHeight>0,"missing media dimensions");
                    Check(Math.Abs(image.ActualWidth/image.ActualHeight-image.Source!.Width/image.Source.Height)<0.01,"distorted image aspect ratio");
                    Check(host.ActualWidth<=image.ActualWidth+6.1,"empty stretched media background");
                    var heading=panel.Children.OfType<Grid>().Single();
                    var desired=Math.Max(image.ActualWidth+6,heading.DesiredSize.Width)+22;
                    Check(bubble.ActualWidth<=desired+1,"empty stretched message bubble");
                    Check(panel.Children.OfType<ChatMessageText>().Single(t=>t.Tag as string=="message-body").Visibility==Visibility.Collapsed,"media-only URL still occupies space");
                    var bounds=bubble.TransformToAncestor(content).TransformBounds(new Rect(bubble.RenderSize));
                    Check(bounds.Right<=size.Width&&bounds.Left>=0,"media clipped at compact width");
                }
            }
            Invoke(w,"ResetChatMedia",true);
            var owner=Guid.Parse(((AccountService)Field(w,"_account")).UserId);
            var peer=((IReadOnlyList<SocialPlayer>)Field(w,"_socialPlayers")).First(p=>p.Relation=="friend").Id;
            const string expired="https://cdn.discordapp.com/attachments/1/2/image.gif?ex=6aa95aef&is=6aa8096f&hm=signature&";
            Set(w,"_socialMessages",(IReadOnlyList<SocialMessage>)new[]{
                new SocialMessage(owner,Guid.NewGuid(),peer,expired,"text",DateTimeOffset.Now.AddMinutes(-2)),
                new SocialMessage(peer,Guid.NewGuid(),owner,expired.Replace("6aa95aef","7fffffff"),"text",DateTimeOffset.Now.AddMinutes(-1))});
            Invoke(w,"RenderSocialMessages");Set(w,"_chatMedia",new ChatMedia(new DeniedFixture()));
            foreach(var bubble in Bubbles(w))
                ((Button)((StackPanel)bubble.Child).Children.OfType<Border>().Single().Child).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            content.Measure(new Size(1050,680));content.Arrange(new Rect(0,0,1050,680));content.UpdateLayout();
            var failed=Bubbles(w).Select(b=>(StackPanel)b.Child).ToArray();
            var expiredHost=failed[0].Children.OfType<Border>().Single();
            Check(expiredHost.Child is TextBlock,"expired link still offers endless retry");
            var notice=(TextBlock)expiredHost.Child;
            const string key="This Discord link has expired. Copy a fresh link in Discord and send it to the chat.";
            Check(notice.Text==UiLanguages.Text(language,"Срок действия ссылки Discord истёк. Скопируйте новую ссылку в Discord и отправьте её в чат.",key),"missing expiry explanation");
            Check(language=="en"||notice.Text!=key,"expiry notice not translated");
            Check(notice.ActualWidth<=360.1&&notice.ActualHeight>0,"expiry notice clipped");
            foreach(var panel in failed)
                Check(panel.Children.OfType<ChatMessageText>().Single(t=>t.Tag as string=="message-body").Visibility==Visibility.Visible,"failed link hidden from copying");
            Check(failed[1].Children.OfType<Border>().Single().Child is Button { IsEnabled:true },"temporary/unclassified failure lost retry");
            Console.WriteLine($"MEDIA LAYOUT PASS {checks} {language}: decoded wide/portrait PNGs, compact bounds, aspect ratio, sender alignment, expired versus retryable links; synthetic media only");
        }
        finally{Invoke(w,"ResetChatMedia",true);w.Close();}
    }
    private sealed class DeniedFixture:HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken token)
        {
            var response=new HttpResponseMessage(HttpStatusCode.Forbidden);
            response.Headers.Date=new DateTimeOffset(2026,9,15,17,0,0,TimeSpan.Zero);return Task.FromResult(response);
        }
    }
    private sealed class Fixture:HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken token)
        {
            bool portrait=request.RequestUri!.AbsolutePath.Contains("portrait");
            int width=portrait?140:420,height=portrait?280:180;var pixels=new byte[width*height*4];
            for(int y=0;y<height;y++)for(int x=0;x<width;x++)
            {
                var i=(y*width+x)*4;pixels[i]=(byte)(110+x*100/width);pixels[i+1]=(byte)(75+y*100/height);pixels[i+2]=(byte)(40+x*90/width);pixels[i+3]=255;
            }
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(BitmapSource.Create(width,height,96,96,PixelFormats.Bgra32,null,pixels,width*4)));
            using var bytes=new MemoryStream();encoder.Save(bytes);
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){Content=new ByteArrayContent(bytes.ToArray())});
        }
    }
}
