using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class MessageCopyChecks
{
    internal static void Run(string language,string output)
    {
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        var w=new MainWindow();var checks=0;
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        object? Invoke(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Message copy: "+why);}
        var content=(FrameworkElement)w.Content;
        void Layout(int width,int height){content.Measure(new Size(width,height));content.Arrange(new Rect(0,0,width,height));content.UpdateLayout();}
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Invoke("ApplyLanguage");SocialChecks.Populate(w,"chat");
            var service=Field<AccountService>("_account");var owner=Guid.Parse(service.UserId);var peer=Field<Guid?>("_socialPeer")!.Value;
            const string body="Отправленное сообщение · sent message\nВыделите часть текста: :ch_treasure_chest: 🙂\nСтрока 3";
            var messages=new[]{new SocialMessage(peer,Guid.NewGuid(),owner,body,"text",DateTimeOffset.UtcNow.AddMinutes(-2)),new SocialMessage(owner,Guid.NewGuid(),peer,"Мой ответ :ch_mana_crystal:","text",DateTimeOffset.UtcNow)};
            Set("_socialMessages",(IReadOnlyList<SocialMessage>)messages);Set("_socialPending",(IReadOnlyList<PendingSocialMessage>)Array.Empty<PendingSocialMessage>());Invoke("RenderSocialMessages");
            string? copied=null;Set("_clipboardWrite",(Action<string>)(value=>copied=value));
            var panel=(StackPanel)w.FindName("FriendsMessagesPanel");
            foreach(var size in new[]{(1050,680),(1600,1000)})
            {
                Layout(size.Item1,size.Item2);
                foreach(var (row,index) in panel.Children.OfType<Grid>().Where(g=>g.Tag is Guid).Select((r,i)=>(r,i)))
                {
                    var bubble=row.Children.OfType<Border>().Single();var stack=(StackPanel)bubble.Child;
                    var text=stack.Children.OfType<ChatMessageText>().Single();var header=stack.Children.OfType<Grid>().Single();
                    var copy=header.Children.OfType<ClipboardButton>().Single();
                    Check(text.IsReadOnly && !text.IsUndoEnabled,"sent message is editable");
                    Check(text.Text==messages[index].Body,"wire text/glyphs changed: "+System.Text.Json.JsonSerializer.Serialize(text.Text)+" expected "+System.Text.Json.JsonSerializer.Serialize(messages[index].Body));
                    Check(text.ActualHeight<100 && text.ActualHeight>=18,"message height bloated/clipped: "+text.ActualHeight);
                    Check(text.ExtentWidth<=text.ViewportWidth+1,"message horizontal overflow");
                    text.SelectAll();copied=null;ApplicationCommands.Copy.Execute(null,text);await Task.Delay(40);
                    Check(copied==messages[index].Body,"Ctrl+C loses glyph tokens/newlines");
                    var run=text.Document.Blocks.OfType<Paragraph>().Single().Inlines.OfType<Run>().First();
                    text.Selection.Select(run.ContentStart,run.ContentStart.GetPositionAtOffset(3)!);copied=null;
                    ApplicationCommands.Copy.Execute(null,text);await Task.Delay(40);Check(copied==messages[index].Body[..3],"partial copy");
                    var old=bubble.ActualHeight;
                    bubble.RaiseEvent(new MouseEventArgs(Mouse.PrimaryDevice,0){RoutedEvent=Mouse.MouseEnterEvent});await Task.Delay(300);Layout(size.Item1,size.Item2);
                    Check(copy.Opacity>.95 && Math.Abs(bubble.ActualHeight-old)<.1,$"hover: opacity={copy.Opacity}, height={old} -> {bubble.ActualHeight}");
                    copied=null;copy.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(60);
                    Check(copied==messages[index].Body,"hover button failed full copy");copy.ResetFeedback();
                    bubble.RaiseEvent(new MouseEventArgs(Mouse.PrimaryDevice,0){RoutedEvent=Mouse.MouseLeaveEvent});await Task.Delay(150);
                    Check(copy.Opacity<.05,"copy button remains after hover");
                }
            }
            var settings=Field<UserSettings>("_settings");var valid=Path.Combine(output,"notification-valid.wav");var invalid=Path.Combine(output,"notification-invalid.wav");
            Directory.CreateDirectory(output);File.WriteAllBytes(valid,NotificationAudio.DefaultBytes());File.WriteAllBytes(invalid,new byte[12]);
            await (Task)Invoke("ImportNotificationSoundAsync",valid)!;
            var saved=File.ReadAllBytes(Path.Combine(ActivityStore.Root,"notification.wav"));var name=settings.NotificationSoundName;
            await (Task)Invoke("ImportNotificationSoundAsync",invalid)!;
            Check(settings.NotificationSoundName==name && saved.SequenceEqual(File.ReadAllBytes(Path.Combine(ActivityStore.Root,"notification.wav"))),"bad sound replaced current sound");
            Check(((Button)w.FindName("NotificationSoundChooseButton")).IsEnabled,"sound import leaves controls disabled");
            var shell=(FrameworkElement)w.Content;Layout(1050,680);
            foreach(var row in panel.Children.OfType<Grid>().Where(g=>g.Tag is Guid))row.Children.OfType<Border>().Single().RaiseEvent(new MouseEventArgs(Mouse.PrimaryDevice,0){RoutedEvent=Mouse.MouseEnterEvent});
            await Task.Delay(150);
            var bitmap=new RenderTargetBitmap(1050,680,96,96,PixelFormats.Pbgra32);bitmap.Render(shell);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var file=File.Create(Path.Combine(output,"message-copy-"+language+".png"));encoder.Save(file);
            Console.WriteLine($"MESSAGE COPY / AUDIO UI PASS [{language}]: {checks}");
        }
        SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(w.Dispatcher));
        try
        {
            var task=Scenario();var frame=new DispatcherFrame();var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(30)};
            timer.Tick+=(_,_)=>frame.Continue=false;timer.Start();_=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(new Action(()=>frame.Continue=false)));
            if(!task.IsCompleted)Dispatcher.PushFrame(frame);timer.Stop();if(!task.IsCompleted)throw new TimeoutException("Message UI checks");task.GetAwaiter().GetResult();
        }
        finally{w.Close();SynchronizationContext.SetSynchronizationContext(null);}
    }
}
