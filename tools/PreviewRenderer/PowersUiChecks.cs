using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class PowersUiChecks
{
    private const BindingFlags Flags = BindingFlags.Instance | BindingFlags.NonPublic;
    private static object? Invoke(MainWindow window, string name, params object?[] values) => typeof(MainWindow).GetMethod(name, Flags)!.Invoke(window, values);
    private static T Field<T>(MainWindow window, string name) => (T)typeof(MainWindow).GetField(name, Flags)!.GetValue(window)!;
    internal static void Populate(MainWindow window)
    {
        var feed = new ChannelManifest { Channel = "beta", Packages = [new() { Id = "powers-shards-original" }] };
        typeof(MainWindow).GetField("_channel", Flags)!.SetValue(window, feed);
        Field<UserSettings>(window, "_settings").DisablePowersAndShards = true;
        Invoke(window, "RefreshModuleAvailability");
    }
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Powers checks require --smoke-test.");
        var window = new MainWindow();
        var count = 0;
        void Check(bool valid, string message) { if (!valid) throw new InvalidOperationException(message); count++; }
        var text = Field<PawsPatchLauncher.Localization>(window, "_text"); text.SetLanguage(language);
        Invoke(window, "ApplyLanguage"); Populate(window); Invoke(window, "SetActivePage", "modules");
        var toggle = (CheckBox)window.FindName("PowersShardsToggle");
        var settings = Field<UserSettings>(window, "_settings");
        Check(toggle.IsChecked == true && toggle.IsEnabled, "Default-on removal switch unavailable with its package.");
        Check(((TextBlock)window.FindName("PowersShardsTitleText")).Text == text["modules.powers"], "Powers switch title is not localized.");
        Check(((TextBlock)window.FindName("PowersShardsDescriptionText")).Text == text["modules.powers.desc"], "Available description is wrong.");
        toggle.IsChecked = false; toggle.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(!settings.DisablePowersAndShards && ConfigurationCode.Create(settings).EndsWith("-PS0"), "Real switch handler does not save the restored-mechanics setting/code.");
        Check(!new SettingsStore().Load().DisablePowersAndShards, "Powers setting does not persist.");
        Invoke(window, "SetBusy", true, null);
        Check(!toggle.IsEnabled, "Busy launcher allows powers changes.");
        Invoke(window, "SetBusy", false, null);
        Check(toggle.IsEnabled, "Powers remains disabled after an operation.");
        toggle.IsChecked = true; toggle.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(settings.DisablePowersAndShards && !ConfigurationCode.Create(settings).Contains("-PS"), "Return to removal changed legacy configuration semantics.");
        typeof(MainWindow).GetField("_channel", Flags)!.SetValue(window, new ChannelManifest());
        Invoke(window, "RefreshModuleAvailability");
        Check(!toggle.IsEnabled && toggle.IsChecked == true, "Old feeds silently enable unsupported restoration.");
        toggle.IsChecked = false; toggle.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(settings.DisablePowersAndShards && toggle.IsChecked == true, "Missing-package guard did not reject restoration.");
        var imported = new UserSettings { DisablePowersAndShards = false };
        Invoke(window, "RestoreSettings", imported, null); Invoke(window, "RefreshModuleAvailability");
        Check(!settings.DisablePowersAndShards && toggle.IsChecked == false && toggle.IsEnabled, "Restored settings are silently reset or cannot return to compatible defaults.");
        toggle.IsChecked = true; toggle.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(settings.DisablePowersAndShards, "Cannot recover legacy mode on an old channel.");
        Populate(window);
        var content = (FrameworkElement)window.Content;
        content.Measure(new Size(1050, 680)); content.Arrange(new Rect(0, 0, 1050, 680)); content.UpdateLayout();
        var heading = (TextBlock)window.FindName("PowersShardsTitleText");
        var description = (TextBlock)window.FindName("PowersShardsDescriptionText");
        Check(heading.FontSize == 15 && heading.TextWrapping == TextWrapping.Wrap && description.FontSize == 13,
            "New component typography differs from existing components.");
        var row = (Grid)heading.Parent;
        foreach (FrameworkElement child in row.Children)
            Check(child.TranslatePoint(new Point(child.ActualWidth, 0), row).X <= row.ActualWidth + .5, "Powers heading/help clipped at minimum size.");
        var help = (Button)window.FindName("PowersShardsHelpButton");
        foreach (var width in new[] { 1050, 1440, 2560 })
        {
            content.Measure(new Size(width, 900)); content.Arrange(new Rect(0, 0, width, 900)); content.UpdateLayout();
            var naturalTitle = new TextBlock { Text = heading.Text, FontFamily = heading.FontFamily, FontSize = heading.FontSize, FontWeight = heading.FontWeight };
            naturalTitle.Measure(new Size(double.PositiveInfinity, double.PositiveInfinity));
            var gap = help.TranslatePoint(new Point(), row).X - heading.TranslatePoint(new Point(), row).X - naturalTitle.DesiredSize.Width;
            Check(Math.Abs(gap - 8) <= 1, $"Powers help is not next to its title at width {width}: {gap}.");
        }
        var helpText = text["modules.powers.help"];
        Check(!helpText.Contains("перед запуском") && !helpText.Contains("совпадать у всех") && !helpText.Contains("before launching") && !helpText.Contains("participants must"), "Redundant launch/multiplayer advice remains in Powers help.");
        Check(helpText.Contains(language == "ru" ? "сохранения" : "saves") && helpText.Contains(language == "ru" ? "Выключено:" : "Off:"), "Powers behavior or save warning was removed.");
        Invoke(window, "SetActivePage", "about");
        Check(((Border)window.FindName("PowersShardsCard")).Visibility == Visibility.Collapsed, "Powers switch leaked into the read-only guide.");
        window.Close();
        Console.WriteLine($"POWERS UI PASS {count} {language}: default on, real handler/persistence, busy state, missing-package guard, recovery/import and narrow layout");
    }
}
