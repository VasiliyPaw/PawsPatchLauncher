using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class ReleaseNotesChecks
{
    internal static void Run(string language,string output)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated profile required");
        new SettingsStore().Save(new UserSettings{Language=language,ModNoticeSeen=true,RebornChannel="beta"});
        var w=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null);
        const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(w,args);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(w)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(w,value);
        T C<T>(string name)=>(T)w.FindName(name);
        var count=0;void Check(bool ok,string reason){if(!ok)throw new Exception("Release notes: "+reason);count++;}
        IEnumerable<T> Desc<T>(DependencyObject root) where T:DependencyObject
        {
            if(root is T value)yield return value;
            foreach(var child in LogicalTreeHelper.GetChildren(root).OfType<DependencyObject>())foreach(var match in Desc<T>(child))yield return match;
        }
        var headings=new Dictionary<string,string[]>{
            ["ru"]=["Режимы игры","Роты и герои","Сохранения и повторы","Интерфейс и настройки","Снабжение и экономика","Совместимость"],
            ["en"]=["Game modes","Companies and heroes","Saves and replays","Interface and settings","Supply and economy","Compatibility"],
            ["uk"]=["Режими гри","Роти та герої","Збереження та повтори","Інтерфейс і налаштування","Постачання та економіка","Сумісність"],
            ["cs"]=["Herní režimy","Roty a hrdinové","Uložené hry a záznamy","Rozhraní a nastavení","Zásobování a ekonomika","Kompatibilita"],
            ["de"]=["Spielmodi","Kompanien und Helden","Spielstände und Wiederholungen","Oberfläche und Einstellungen","Versorgung und Wirtschaft","Kompatibilität"],
            ["fr"]=["Modes de jeu","Compagnies et héros","Sauvegardes et rediffusions","Interface et paramètres","Ravitaillement et économie","Compatibilité"]};
        var ru="## Режимы игры\n- Vanilla, Immortals и Arcane Wars объединены; Vanilla выбрана по умолчанию.\n- Добавлены армии шести рас и герои для Vanilla.\n\n## Роты и герои\n- Перенесены опыт, мораль, бегство и ручной отход.\n- Обновлены панели рот, знамёна, портреты героев и группы.\n- Герои назначаются в роты, пересаживаются и возвращаются в резерв.\n\n## Сохранения и повторы\n- Полное сохранение партии, три автосохранения и восстановление сетевых мест.\n- Повторы с паузой, скоростью и перемоткой.\n\n## Интерфейс и настройки\n- Переработаны миникарта, снабжение, меню и поиск игр.\n- Добавлены четыре схемы клавиш, уведомления и звуки предупреждений.\n- Графика применяется прямо в матче; настройки сохраняются.\n\n## Снабжение и экономика\n- При нехватке содержания роты вне снабжения теряют здоровье.\n- Дефицит замедляет пополнение и лечение, останавливает ремонт.\n\n## Совместимость\n- Для сети нужна одинаковая версия у всех игроков. Старые форматы сохранений не поддерживаются.";
        var notes=headings.ToDictionary(p=>p.Key,p=>p.Key=="ru"?ru:string.Join("\n\n",p.Value.Select(title=>"## "+title+"\n- "+title+" — Unicode: І, Č, ä, é.\n- "+string.Join(' ',Enumerable.Repeat(title,8)))));
        var build=new RebornBuild(Guid.NewGuid(),"beta","0.58.0",123,new('A',64),"KohanReborn.exe",DateTimeOffset.Parse("2026-11-17T12:00:00Z"),notes);
        var older=build with{Id=Guid.NewGuid(),Version="0.57.0",PublishedAt=build.PublishedAt.AddDays(-1)};
        var stable=build with{Id=Guid.NewGuid(),Channel="stable",Version="0.56.0",PublishedAt=build.PublishedAt.AddDays(-2)};
        var panel=C<StackPanel>("NewsEntriesPanel");var scroll=C<ScrollViewer>("NewsScrollViewer");
        var host=new Window{Width=880,Height=340,Left=-32000,Top=-32000,Opacity=0,ShowActivated=false,ShowInTaskbar=false,WindowStyle=WindowStyle.None,WindowStartupLocation=WindowStartupLocation.Manual,Title="Release notes isolated layout fixture"};
        Border[] Cards()=>panel.Children.OfType<Border>().Where(c=>c.Tag is string[]).ToArray();
        Border Card(string version)=>Cards().Single(c=>((string[])c.Tag).Any(k=>k.Contains(":"+version+":")));
        StackPanel Body(Border card)=>((StackPanel)card.Child).Children.OfType<StackPanel>().Single(p=>Equals(p.Tag,"changelog-body"));
        Button Toggle(Border card)=>((StackPanel)card.Child).Children.OfType<Button>().Single();
        int HeadingCount(Panel body)=>body.Children.OfType<TextBlock>().Count(t=>t.FontWeight==FontWeights.SemiBold);
        async Task Layout()
        {
            scroll.Measure(new Size(860,300));scroll.Arrange(new Rect(0,0,860,300));scroll.UpdateLayout();
            await Dispatcher.Yield(DispatcherPriority.ApplicationIdle);
            scroll.UpdateLayout();
        }
        async Task Scenario()
        {
            var account=Field<AccountService>("_account");
            typeof(AccountService).GetField("_session",flags)!.SetValue(account,new AccountSession{UserId=Guid.NewGuid().ToString(),Nickname="fixture",Email="fixture@example.invalid",PawsTeam=true});
            typeof(AccountService).GetProperty("State")!.SetValue(account,AccountState.SignedIn);
            Call("RenderAccount");Set("_activePage","reborn");Set("_rebornBuilds",(IReadOnlyList<RebornBuild>)new[]{build});
            Call("RenderReborn");
            var pageNotes=Desc<StackPanel>(C<StackPanel>("RebornBody")).Single(p=>Equals(p.Tag,"reborn-release-notes"));
            var blocks=pageNotes.Children.OfType<TextBlock>().ToArray();
            Check(HeadingCount(pageNotes)==6,"Reborn page has no formatted section headings");
            Check(blocks.Where(t=>t.FontWeight==FontWeights.SemiBold).Select(t=>t.Text).SequenceEqual(headings[language]),"wrong translated headings");
            Check(blocks.All(t=>!t.Text.StartsWith("##")&&!t.Text.StartsWith("- ")&&t.TextWrapping==TextWrapping.Wrap),"raw markdown or clipped text");
            Check(blocks.Count(t=>t.Text.StartsWith("• "))==(language=="ru"?13:12),"bullets were lost");
            Check(blocks.First().FontSize==15&&blocks.First().Foreground.ToString()=="#FFE7D099","heading style differs from launcher history");
            ((Panel)pageNotes.Parent).Children.Remove(pageNotes);
            var preview=new Border{Width=940,Padding=new Thickness(24),Background=new SolidColorBrush(Color.FromRgb(16,34,56)),Child=pageNotes};
            preview.Measure(new Size(940,double.PositiveInfinity));preview.Arrange(new Rect(new Point(),preview.DesiredSize));preview.UpdateLayout();
            var bitmap=new RenderTargetBitmap(940,(int)Math.Ceiling(preview.ActualHeight),96,96,PixelFormats.Pbgra32);bitmap.Render(preview);
            Directory.CreateDirectory(output);var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using(var file=File.Create(Path.Combine(output,"reborn-notes-"+language+".png")))encoder.Save(file);
            ((Grid)scroll.Parent).Children.Remove(scroll);
            host.Content=scroll;host.Show();
            Set("_rebornHistory",(IReadOnlyList<RebornBuild>)new[]{build,older,stable});Set("_rebornHistoryLoaded",true);
            Set("_historySubject","reborn");Set("_historySource","all");Set("_historyBranch","beta");Set("_historyActiveSelection","reborn:beta");
            Call("RefreshNews");await Layout();
            var first=Card(build.Version);Toggle(first).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Layout();
            Check(HeadingCount(Body(first))==6,"expanded history lost headings");
            scroll.ScrollToVerticalOffset(120);await Layout();Check(scroll.VerticalOffset>100,$"fixture needs a scrolled long entry: offset={scroll.VerticalOffset}, extent={scroll.ExtentHeight}, viewport={scroll.ViewportHeight}");
            var beforeY=first.TranslatePoint(new Point(),scroll).Y;
            Set("_rebornHistoryLoading",true);Call("RefreshNews");await Layout();
            Check(ReferenceEquals(first,Card(build.Version))&&HeadingCount(Body(first))==6,"loading poll rebuilt/collapsed a loaded entry");
            Set("_rebornHistoryLoading",false);Call("RefreshNews");await Layout();
            Check(ReferenceEquals(first,Card(build.Version)),"poll completion rebuilt unchanged cards");
            var newest=build with{Id=Guid.NewGuid(),Version="0.59.0",PublishedAt=build.PublishedAt.AddDays(1)};
            Set("_rebornHistory",(IReadOnlyList<RebornBuild>)new[]{newest,build,older,stable});Call("RefreshNews");await Layout();
            Check(HeadingCount(Body(Card(build.Version)))==6&&HeadingCount(Body(Card(newest.Version)))<6,"refresh lost per-entry expansion state");
            Check(Math.Abs(Card(build.Version).TranslatePoint(new Point(),scroll).Y-beforeY)<1,"new release moved the currently read entry");
            Set("_rebornHistoryError",true);Call("RefreshNews");await Layout();
            Check(HeadingCount(Body(Card(build.Version)))==6&&Math.Abs(Card(build.Version).TranslatePoint(new Point(),scroll).Y-beforeY)<1,"error status lost reading state");
            Set("_rebornHistoryError",false);Call("RefreshNews");await Layout();
            Toggle(Card(build.Version)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Layout();
            var edited=build with{Notes=notes.ToDictionary(p=>p.Key,p=>p.Value+"\n- Unicode: Č, І, é.")};
            Set("_rebornHistory",(IReadOnlyList<RebornBuild>)new[]{newest,edited,older,stable});Call("RefreshNews");await Layout();
            Check(HeadingCount(Body(Card(build.Version)))<6,"manual collapse was forgotten on refresh");
            Toggle(Card(build.Version)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Layout();
            Set("_rebornHistory",(IReadOnlyList<RebornBuild>)new[]{newest,build,older,stable});Call("RefreshNews");await Layout();
            Check(HeadingCount(Body(Card(build.Version)))==6,"edited notes collapsed the same release");
            await (Task)Call("SwitchHistoryAsync","reborn","all","stable")!;await Layout();
            Check(scroll.VerticalOffset==0,"manual filter change did not reset scroll");
            Check(!w.IsLoaded&&!w.IsVisible,"launcher window was shown");
            File.WriteAllText(Path.Combine(output,"release-notes-"+language+".json"),JsonSerializer.Serialize(new{passed=true,language,checks=count,headless=true}));
            Console.WriteLine($"RELEASE NOTES PASS {count} {language}: shared headings/bullets, polling, expansion, edits and scroll anchor; no launcher/game window shown");
        }
        try
        {
            var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();
            var deadline=new DispatcherTimer{Interval=TimeSpan.FromSeconds(30)};deadline.Tick+=(_,_)=>frame.Continue=false;
            _=task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false));deadline.Start();Dispatcher.PushFrame(frame);deadline.Stop();
            if(!task.IsCompleted)throw new TimeoutException("Release notes fixture");task.GetAwaiter().GetResult();
        }
        finally{host.Close();w.Close();}
    }
}
