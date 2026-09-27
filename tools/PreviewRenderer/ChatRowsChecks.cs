using System.Collections;
using System.Diagnostics;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class ChatRowsChecks
{
    internal static void Run(string language)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated fixtures required.");
        var w=new MainWindow();const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        var panel=(StackPanel)w.FindName("FriendsMessagesPanel");var count=0;
        void Check(bool ok,string why){count++;if(!ok)throw new Exception("Incremental chat: "+why);}
        Dictionary<Guid,FrameworkElement> Rows()=>panel.Children.OfType<FrameworkElement>().Where(e=>e.Tag is Guid).ToDictionary(e=>(Guid)e.Tag);
        void Layout(){var c=(FrameworkElement)w.Content;c.Measure(new Size(1440,900));c.Arrange(new Rect(0,0,1440,900));c.UpdateLayout();}
        try
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);Call("ApplyLanguage");
            // Loaded image controls must survive a send without another fetch/decoder.
            MediaLayoutChecks.Populate(w);Layout();
            var mediaRows=Rows();var media=Field<IDictionary>("_mediaRows").Values.Cast<object>().ToArray();
            var account=Field<AccountService>("_account");var owner=Guid.Parse(account.UserId);
            var peer=Field<Guid?>("_socialPeer")!.Value;
            var pending=new PendingSocialMessage(owner,peer,Guid.NewGuid(),"Synthetic send","text");
            Set("_socialPending",new[]{pending});Call("RenderSocialMessages");Layout();
            Check(mediaRows.All(p=>ReferenceEquals(p.Value,Rows()[p.Key])),"send rebuilt loaded media rows");
            Check(media.SequenceEqual(Field<IDictionary>("_mediaRows").Values.Cast<object>()),"send cancelled media lifetimes");
            var messages=Enumerable.Range(0,200).Select(i=>new SocialMessage(peer,Guid.NewGuid(),owner,"Synthetic message "+i,"text",DateTimeOffset.Now.AddSeconds(i-300))).ToArray();
            Set("_socialMessages",messages);Set("_socialPending",Array.Empty<PendingSocialMessage>());Call("RenderSocialMessages");Layout();
            Check(Field<IDictionary>("_mediaRows").Count==0,"removed media leaked");
            var before=Rows();var clock=Stopwatch.StartNew();
            Set("_socialPending",new[]{pending});Call("RenderSocialMessages");Layout();clock.Stop();
            Check(before.Count==200&&before.All(p=>ReferenceEquals(p.Value,Rows()[p.Key])),"send rebuilt existing history");
            var pendingRow=Rows()[pending.Id];
            Set("_socialPending",new[]{pending with {Error="delivery_timeout"}});Call("RenderSocialMessages");
            Check(!ReferenceEquals(pendingRow,Rows()[pending.Id])&&before.All(p=>ReferenceEquals(p.Value,Rows()[p.Key])),"error did not replace just its row");
            var sent=new SocialMessage(owner,pending.Id,peer,pending.Body,"text",pending.CreatedAt);
            Set("_socialMessages",messages.Append(sent).ToArray());Set("_historyViewStart",1);Set("_socialPending",Array.Empty<PendingSocialMessage>());Call("RenderSocialMessages");Layout();
            Check(Rows().Count==200&&Rows().ContainsKey(sent.MessageId)&&!Rows().ContainsKey(messages[0].MessageId),"ack/history bound produced duplicate or missing rows");
            Check(messages.Skip(1).All(m=>ReferenceEquals(before[m.MessageId],Rows()[m.MessageId])),"history window shift rebuilt retained rows");
            Set("_historyViewStart",0);Call("RenderSocialMessages");
            Check(Rows().Count==200&&Rows().ContainsKey(messages[0].MessageId),"older page did not restore head");
            Set("_socialMessages",messages.Take(2).ToArray());Set("_historyRevision",Field<long>("_historyRevision")+1);Call("RenderSocialMessages");
            Check(Rows().Count==2&&Field<IDictionary>("_messageRows").Count<=4,"trim retained stale controls");
            Set("_socialPeer",Guid.NewGuid());Set("_socialMessages",Array.Empty<SocialMessage>());Call("RenderSocialMessages");
            Check(panel.Children.Count==0&&Field<IDictionary>("_messageRows").Count==0,"peer switch retained prior conversation");
            Call("ResetChatMedia",true);Check(Field<IDictionary>("_mediaRows").Count==0,"dispose leaked media");
            Console.WriteLine($"CHAT ROWS PASS {count} {language}; 200-row append and layout {clock.Elapsed.TotalMilliseconds:F1}ms; synthetic messages, retained controls/media, failure, ack, paging, trim and peer isolation");
        }
        finally{w.Close();}
    }
}
