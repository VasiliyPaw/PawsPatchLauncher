using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private sealed record DiagnosticLogChoice(int Count,string Label);
    private Window CreateDiagnosticsOptionsDialog(Action<DiagnosticOptions> select,DiagnosticLocations? testLocations = null)
    {
        var (window,body) = CreateCommunityDialog(T("Архив диагностики","Diagnostic archive"),IconKind.Diagnostics,620,560);
        window.MinHeight = 0; window.SizeToContent = SizeToContent.Height; window.Height = double.NaN;
        window.MaxHeight = SystemParameters.WorkArea.Height-32;
        var panel = new StackPanel();
        body.Content = new ScrollViewer { Content = panel,VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,MaxHeight = Math.Max(200,window.MaxHeight-100) };
        TextBlock Text(string text,int size=13) => new() { Text=text,FontSize=size,Foreground=SocialBrush("#B5C7DC"),TextWrapping=TextWrapping.Wrap };
        panel.Children.Add(Text(T("Выберите, сколько последних логов игры добавить в архив.","Choose how many recent game logs to include in the archive."),15));
        var caption = Text(T("Количество наборов логов","Number of log sets"));caption.Margin=new Thickness(0,20,0,8);panel.Children.Add(caption);
        var choices = new[] {0,1,3,5,10,20,50,100,int.MaxValue}.Select(n=>new DiagnosticLogChoice(n,n==0 ? T("Без логов игры","No game logs") : n==int.MaxValue ? T("Все","All") : n.ToString())).ToArray();
        var count = new ComboBox { Name="DiagnosticLogCount",Style=(Style)FindResource("ReleaseCombo"),ItemsSource=choices,DisplayMemberPath="Label",SelectedIndex=2,IsEnabled=_game is not null };
        System.Windows.Automation.AutomationProperties.SetName(count,caption.Text);panel.Children.Add(count);
        var dumps = new CheckBox { Name="DiagnosticIncludeDumps",Content=T("Добавить дампы сбоев","Include crash dumps"),IsChecked=true,IsEnabled=_game is not null,Margin=new Thickness(0,14,0,10) };
        panel.Children.Add(dumps);
        panel.Children.Add(Text(T("Основной лог и ART считаются одним набором. С дампами также добавляются относящиеся к ним логи сбоев.","The main log and ART count as one set. Crash dumps also include their companion crash logs."),12));
        var estimate = Text(T("Оцениваем размер…","Estimating size…"),20);estimate.Name="DiagnosticSizeEstimate";estimate.FontWeight=FontWeights.SemiBold;estimate.Foreground=SocialBrush("#EAD096");
        var details = Text("");details.Name="DiagnosticSelectionDetails";details.Margin=new Thickness(0,8,0,0);
        panel.Children.Add(new Border { Background=SocialBrush("#172D46"),BorderBrush=SocialBrush("#40536E"),BorderThickness=new Thickness(1),CornerRadius=new CornerRadius(8),Padding=new Thickness(16),Margin=new Thickness(0,18,0,12),Child=new StackPanel { Children={estimate,details} } });
        panel.Children.Add(Text(_game is null ? T("Игра не выбрана. В архив войдёт только диагностика лаунчера.","No game is selected. The archive will contain launcher diagnostics only.")
            : T("Размер приблизительный: сжатие и новые записи в логах могут его изменить. Логи лаунчера и сведения о системе добавляются всегда.","The size is approximate: compression and new log entries may change it. Launcher logs and system information are always included."),12));
        var actions = new StackPanel { Orientation=Orientation.Horizontal,HorizontalAlignment=HorizontalAlignment.Right,Margin=new Thickness(0,20,0,0) };
        var cancel = new Button { Name="DiagnosticCancel",Content=T("Отмена","Cancel"),Style=(Style)FindResource("GhostButton"),Margin=new Thickness(0,0,10,0) };
        var create = new Button { Name="DiagnosticCreate",Content=T("Создать архив","Create archive"),Style=(Style)FindResource("GoldButton"),IsEnabled=false };
        LauncherIcon.SetKind(create,IconKind.Diagnostics);actions.Children.Add(cancel);actions.Children.Add(create);panel.Children.Add(actions);
        var gameRoot=_game?.Directory;
        DiagnosticOptions Selected() => new(gameRoot is null ? 0 : ((DiagnosticLogChoice)count.SelectedItem).Count,gameRoot is not null && dumps.IsChecked==true && ((DiagnosticLogChoice)count.SelectedItem).Count>0);
        CancellationTokenSource? pending=null;var version=0;var closed=false;
        var delay=new DispatcherTimer {Interval=TimeSpan.FromMilliseconds(200)};
        async Task Update()
        {
            delay.Stop();var current=++version;pending?.Cancel();pending?.Dispose();pending=new();var token=pending.Token;
            var selected=Selected();create.IsEnabled=false;dumps.IsEnabled=gameRoot is not null && selected.RecentCount>0;
            estimate.Text=T("Оцениваем размер…","Estimating size…");details.Text="";
            try
            {
                var report=await Task.Run(()=>DiagnosticsCollector.PreviewAsync(gameRoot,selected,token,ActivityStore.IsSmokeTest?testLocations:null),token);
                if(closed||current!=version)return;
                estimate.Text=T("Примерный размер архива: ","Estimated archive size: ")+"≈ "+DiagnosticSize(report.EstimatedArchiveBytes);
                var files=report.Files.Where(f=>f.Status=="estimated").ToArray();
                details.Text=string.Format(T("Логов игры: {0} · Дампов и отчётов: {1}","Game log files: {0} · Dumps and reports: {1}"),files.Count(f=>f.Category is "game-logs" or "sync-logs"),files.Count(f=>f.Category is "game-dumps" or "full-memory-dumps" or "windows-dumps" or "windows-reports"));
                if(report.Files.Any(f=>f.Status=="failed"))details.Text+="\n"+T("Некоторые файлы недоступны и могут не попасть в архив.","Some files are unavailable and may be omitted from the archive.");
                create.IsEnabled=true;
            }
            catch(OperationCanceledException) { }
            catch(Exception error) when(error is IOException or UnauthorizedAccessException or ArgumentException)
            {
                if(closed||current!=version)return;
                estimate.Text=T("Не удалось оценить размер","Could not estimate the size");details.Text=T("Архив можно создать без предварительной оценки.","You can create the archive without a size estimate.");create.IsEnabled=true;
            }
        }
        void Queue() { if(!window.IsLoaded)return;version++;pending?.Cancel();create.IsEnabled=false;estimate.Text=T("Оцениваем размер…","Estimating size…");delay.Stop();delay.Start(); }
        delay.Tick+=async(_,_)=>await Update();count.SelectionChanged+=(_,_)=>Queue();dumps.Checked+=(_,_)=>Queue();dumps.Unchecked+=(_,_)=>Queue();
        window.Loaded+=async(_,_)=>await Update();
        window.Closed+=(_,_)=>{closed=true;version++;delay.Stop();pending?.Cancel();pending?.Dispose();};
        cancel.Click+=(_,_)=>window.Close();create.Click+=(_,_)=>{if(create.IsEnabled){select(Selected());window.Close();}};
        return window;
    }
    private static string DiagnosticSize(long bytes) => bytes>=1073741824 ? $"{bytes/1073741824d:0.0} GB" : bytes>=1048576 ? $"{bytes/1048576d:0.0} MB" : $"{Math.Max(1,bytes/1024d):0} KB";
}
