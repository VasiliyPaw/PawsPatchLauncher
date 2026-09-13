using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class LauncherEvolutionChecks
{
    public static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new Exception("Isolated test required");
        new SettingsStore().Save(new UserSettings { ModNoticeSeen = true, Language = language });
        var w=new MainWindow(new LauncherConfiguration { FeedUrls=[], BetaFeedUrls=[] },null) {
            Width=1440,Height=900,Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual };
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        T C<T>(string name)=>(T)w.FindName(name);
        var count=0;void Check(bool ok,string why) {count++;if(!ok)throw new Exception("Launcher evolution UI: "+why);}
        void Save(string name) {
            w.UpdateLayout();Directory.CreateDirectory(output);
            var frame=new RenderTargetBitmap((int)w.ActualWidth,(int)w.ActualHeight,96,96,PixelFormats.Pbgra32);frame.Render(w);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(frame));using var stream=File.Create(Path.Combine(output,name+"-"+language+".png"));encoder.Save(stream);
        }
        try
        {
            w.Show(); SocialChecks.Populate(w,"chat"); Call("SetActivePage","friends"); w.UpdateLayout();
            var composer=C<ChatComposer>("FriendsMessageInput");
            foreach(var glyph in ChatGlyphs.All)
            {
                composer.Clear();composer.InsertGlyph(glyph);
                Check(composer.Text==glyph.Token,"Glyph wire representation broken: "+glyph.Id);
                Check(((Paragraph)composer.Document.Blocks.FirstBlock).Inlines.OfType<InlineUIContainer>().Count()==1,"Composer did not render original glyph");
                composer.Undo(); Check(composer.Text=="","Glyph insertion cannot be undone");
            }
            var all=string.Join(" ",ChatGlyphs.All.Select(g=>g.Token));
            composer.Text="Сообщение / Message\n"+all+"\n";
            Check(composer.Text=="Сообщение / Message\n"+all+"\n","Text/newline/glyph roundtrip lost content");
            string? copied=null;composer.CopyTextRequested=text=>{copied=text;return Task.FromResult(true);};
            composer.Text=":ch_mana_crystal:";composer.SelectAll();System.Windows.Input.ApplicationCommands.Copy.Execute(null,composer);
            Check(copied==":ch_mana_crystal:","Copy lost glyph token");
            System.Windows.Input.ApplicationCommands.Cut.Execute(null,composer);Check(composer.Text=="","Cut did not delete the copied glyph");
            composer.Text="unchanged";composer.SelectAll();composer.CopyTextRequested=_=>Task.FromResult(false);
            System.Windows.Input.ApplicationCommands.Cut.Execute(null,composer);Check(composer.Text=="unchanged","Failed copy deleted text");
            composer.SelectAll();composer.InsertText("replacement");Check(composer.Text=="replacement","Selection replacement failed");
            composer.Text=new string('x',1999); composer.CaretPosition=composer.Document.ContentEnd;
            composer.InsertGlyph(ChatGlyphs.All[0]);Check(composer.Text==new string('x',1999),"Glyph exceeded message limit");
            composer.Text="Draft :ch_mana_crystal:"; var draft=composer.Text;Call("ApplyLanguage");Check(composer.Text==draft,"Language refresh destroyed draft");
            composer.Text="<b>plain text</b> :ch_unknown: ";Check(composer.Text=="<b>plain text</b> :ch_unknown: ","Unknown tokens/markup were interpreted");
            var text=new TextBlock();ChatGlyphs.Render(text,all,language=="ru");
            Check(text.Inlines.OfType<InlineUIContainer>().Count()==26,"Not all original images rendered in messages");
            var rows=C<StackPanel>("FriendsMessagesPanel"); rows.Children.Add(new Border { Padding=new(12),Child=text });
            composer.Text=(language=="ru"?"Готов к игре! ":"Ready to play! ")+":ch_mana_crystal: :ch_treasure_chest: :ch_sword_on_shield:";
            Save("chat-glyphs");
            Call("FriendsGlyph_Click",C<Button>("FriendsGlyphButton"),new RoutedEventArgs());
            var popup=Field<Grid>("_chatPopup");
            Check(popup.Visibility==Visibility.Visible,"Glyph picker not open");Call("RemoveChatPopup");
            Call("SetActivePage","modules");
            Set("_compatibilityState",GameCompatibilityState.Unsupported);Set("_selectedHasInstalledPatch",false);Set("_compatibilityNoticeKey","uninstalled");
            Call("RenderCompatibility"); Check(Field<Border?>("_compatibilityPopup") is null,"Uninstalled mod triggered an automatic popup");
            Set("_selectedHasInstalledPatch",true);Set("_compatibilityNoticeKey","stored-old");Call("RenderCompatibility");
            Check(Field<Border?>("_compatibilityPopup") is not null,"Installed old mod did not show its compatibility popup");
            Call("CloseCompatibilityPopup");Set("_compatibilityState",GameCompatibilityState.Supported);Set("_installedRuntimeMismatch",false);Set("_lastProbeDataOnly",false);Call("RenderCompatibility");
            Check(C<Border>("CompatibilityBanner").Visibility==Visibility.Collapsed,"Compatible selection retained the red banner");
            Check(Field<Border?>("_compatibilityPopup") is null,"Compatible selection retained the popup");
            Save("components");
            Console.WriteLine($"LAUNCHER EVOLUTION UI PASS {count} ({language})");
        }
        finally { w.Close(); }
    }
}
