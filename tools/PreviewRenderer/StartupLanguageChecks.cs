using System.Globalization;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class StartupLanguageChecks
{
    internal static void Run()
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Fixture only");
        var path=Path.Combine(ActivityStore.Root,"settings.json");
        if(File.Exists(path))throw new InvalidOperationException("Run startup-language checks in a fresh smoke process.");
        var previous=CultureInfo.CurrentUICulture;
        var count=0;
        void Check(bool ok,string reason){count++;if(!ok)throw new Exception("Startup language UI: "+reason);}
        string Language(MainWindow w)=>((PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text",BindingFlags.NonPublic|BindingFlags.Instance)!.GetValue(w)!).Language;
        try
        {
            CultureInfo.CurrentUICulture=CultureInfo.GetCultureInfo("ru-RU");
            var first=new MainWindow();
            try
            {
                Check(Language(first)=="en","first window followed Russian OS culture");
                Check(((TextBlock)first.FindName("TitleText")).Text=="Paw's Patch for Kohan II","initial title not English");
                ((Button)first.FindName("LanguageButton")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Check(Language(first)=="ru"&&new SettingsStore().Load().Language=="ru","language button did not persist Russian");
            }
            finally{first.Close();}
            var second=new MainWindow();
            try
            {
                Check(Language(second)=="ru","restart discarded saved Russian");
                Check(((TextBlock)second.FindName("TitleText")).Text=="Paw's Patch для Kohan II","saved Russian title not applied");
                ((Button)second.FindName("SettingsLanguageButton")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Check(Language(second)=="en"&&new SettingsStore().Load().Language=="en","settings language button did not persist English");
            }
            finally{second.Close();}
            var third=new MainWindow();
            try{Check(Language(third)=="en","restart discarded saved English");}
            finally{third.Close();}
        }
        finally{CultureInfo.CurrentUICulture=previous;}
        Console.WriteLine($"STARTUP LANGUAGE UI PASS {count}: fresh English on Russian Windows culture, both buttons and saved RU/EN across windows; isolated smoke preferences");
    }
}
