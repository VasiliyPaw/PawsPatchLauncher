using System.Windows;

namespace PawsPatchLauncher;

public partial class App : Application
{
    private void Tooltip_Loaded(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement tooltip) { tooltip.UpdateLayout(); Motion.Reveal(tooltip); }
    }

    private System.Threading.Mutex? _instance;
    public static bool PreviousUncleanExit { get; private set; }
    private RunRecord? _run;
    protected override void OnStartup(StartupEventArgs e)
    {
        if (ActivityStore.IsSmokeTest) TestProcessErrorMode.Enable();
        _instance = new System.Threading.Mutex(true, "Local\\PawsPatchLauncher-Reliability" + (ActivityStore.IsSmokeTest ? "-smoke-" + Environment.ProcessId : ""), out var first);
        if (!first) { Shutdown(); return; }
        var previous = ActivityStore.Read("launcher-run");
        PreviousUncleanExit = previous is { CleanExit: false } && !ActivityStore.IsAlive(previous);
        _run = ActivityStore.ForProcess(System.Diagnostics.Process.GetCurrentProcess());
        ActivityStore.Save("launcher-run", _run);
        DispatcherUnhandledException += (_, args) =>
        {
            ActivityStore.Log(args.Exception);
            if (ActivityStore.IsSmokeTest)
            {
                Console.Error.WriteLine(args.Exception);
                // Do not show a modal error over the user's game or let a failed test pass.
                Environment.Exit(1);
                return;
            }
            MessageBox.Show(args.Exception.Message, "Paw's Patch Launcher", MessageBoxButton.OK, MessageBoxImage.Error);
            args.Handled = true;
        };
        ShellIcon.RefreshExecutable();
        base.OnStartup(e);
    }

    protected override void OnExit(ExitEventArgs e)
    {
        if (_run is not null) { _run.CleanExit = true; ActivityStore.Save("launcher-run", _run); }
        _instance?.Dispose();
        base.OnExit(e);
    }
}
