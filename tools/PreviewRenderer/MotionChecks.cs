using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Shapes;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class MotionChecks
{
    internal static void Run(MainWindow window)
    {
        int checks = 0;
        void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); checks++; }
        void Pump(int milliseconds)
        {
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer(DispatcherPriority.Background) { Interval = TimeSpan.FromMilliseconds(milliseconds) };
            timer.Tick += (_, _) => frame.Continue = false;
            timer.Start();
            try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
        }
        T Part<T>(Control control, string name) where T : DependencyObject => (T)control.Template.FindName(name, control);
        Color ColorOf(Border border) => ((SolidColorBrush)border.Background).Color;
        bool Same(Color left, Color right) => left.A == right.A && left.R == right.R && left.G == right.G && left.B == right.B;
        double Position(CheckBox control) => (Part<Ellipse>(control, "Thumb").RenderTransform as TranslateTransform)?.X ?? 0;
        var switchStyle = (Style)window.FindResource("ToggleSwitch");
        var a = new CheckBox { Style = switchStyle };
        var b = new CheckBox { Style = switchStyle };
        var preset = new CheckBox { Style = switchStyle, IsChecked = true, IsEnabled = false };
        var ordinary = new CheckBox { Content = "Cleanup selection" };
        var radio = new RadioButton { Style = (Style)window.FindResource("ModeRadio"), Content = "Standard" };
        var button = new Button { Style = (Style)window.FindResource("GhostButton"), Content = "Button" };
        var grip = new Thumb { Style = (Style)window.FindResource("ScrollGrip"), Width = 13, Height = 70 };
        var panel = new StackPanel { Width = 360 };
        foreach (var item in new FrameworkElement[] { a, b, preset, ordinary, radio, button, grip }) panel.Children.Add(item);
        // Real WPF animation frames need a presentation source. This isolated, off-screen window
        // never activates, appears in the taskbar, changes settings or touches the user's launcher.
        var testWindow = new Window
        {
            Content = panel,
            Width = 380,
            Height = 620,
            Left = -32000,
            Top = -32000,
            WindowStartupLocation = WindowStartupLocation.Manual,
            WindowStyle = WindowStyle.None,
            ShowActivated = false,
            ShowInTaskbar = false,
            IsHitTestVisible = false
        };
        try
        {
            testWindow.Show();
            panel.Measure(new Size(360, 600)); panel.Arrange(new Rect(0, 0, 360, 600)); panel.UpdateLayout();
            Pump(40);
            var track = Part<Border>(a, "Track");
            var off = ColorOf(track);
            var goldResource = (SolidColorBrush)window.FindResource("GoldBrush");
            var gold = goldResource.Color;
            Check(Position(preset) == 21 && Same(ColorOf(Part<Border>(preset, "Track")), gold), "Preselected switch flashed its unchecked state.");
            Check(Math.Abs(Part<Grid>(preset, "SwitchVisual").Opacity - 0.45) < 0.001, "Disabled initial state is wrong.");
            var events = 0; a.Checked += (_, _) => events++;
            a.IsChecked = true;
            Check(a.IsChecked == true && events == 1, "Visual transition delayed the logical setting.");
            var moving = SystemParameters.ClientAreaAnimation;
            if (moving)
            {
                Check(Position(a) < 21, "Switch jumped to the endpoint.");
                Pump(55);
                Check(Position(a) > 0 && Position(a) < 21, "Switch has no intermediate position.");
                Check(!Same(ColorOf(track), off) && !Same(ColorOf(track), gold), "Track has no intermediate color.");
                var beforeReverse = Position(a);
                a.IsChecked = false;
                Check(Math.Abs(Position(a) - beforeReverse) < 1, "Reversing a switch jumped to its old endpoint.");
            }
            else a.IsChecked = false;
            Pump(260);
            Check(Math.Abs(Position(a)) < 0.001 && Same(ColorOf(track), off), "Reverse animation did not settle.");
            for (int i = 0; i < 12; i++) { a.IsChecked = i % 2 == 0; Pump(10); Check(Position(a) >= 0 && Position(a) <= 21, "Switch overshot its bounds."); }
            a.IsChecked = true; Pump(270);
            Check(Position(a) == 21 && Same(ColorOf(track), gold), "Rapid clicks ended in the wrong visual state.");
            Check(Position(b) == 0 && Same(ColorOf(Part<Border>(b, "Track")), off), "Animation leaked into another switch.");
            Check(goldResource.Color == gold && !goldResource.HasAnimatedProperties, "Shared theme brush was mutated.");
            ordinary.IsChecked = true; radio.IsChecked = true;
            if (moving) { Pump(45); Check(Part<Path>(ordinary, "CheckMark").Opacity is > 0 and < 1, "Checkbox tick did not fade."); }
            Pump(220);
            Check(Part<Path>(ordinary, "CheckMark").Opacity == 1, "Checkbox tick did not settle.");
            Check(Same(ColorOf(Part<Border>(radio, "ModeBorder")), (Color)ColorConverter.ConvertFromString("#4A3C20")), "Radio option did not settle.");
            a.IsEnabled = false; Pump(210);
            Check(Math.Abs(Part<Grid>(a, "SwitchVisual").Opacity - 0.45) < 0.001, "Disabled opacity did not settle.");
            a.IsEnabled = true; Pump(210);
            Check(Part<Grid>(a, "SwitchVisual").Opacity == 1, "Enabled opacity did not recover.");

            // Exercise the same presentation targets used by the real hover/drag triggers.
            foreach (var (control, part) in new (Control, string)[] { (button, "Border"), (grip, "Grip") })
            {
                Check(control.Template.Triggers.OfType<Trigger>().Any(t => t.Property == UIElement.IsMouseOverProperty
                    && t.Setters.OfType<Setter>().Any(s => s.Property == Motion.BackgroundProperty)), "Hover trigger bypasses transitions.");
                var surface = Part<Border>(control, part);
                var original = ColorOf(surface);
                Motion.SetBackground(surface, goldResource);
                if (moving) { Pump(45); Check(!Same(ColorOf(surface), original) && !Same(ColorOf(surface), gold), "Hover color did not interpolate."); }
                Motion.SetBackground(surface, new SolidColorBrush(original)); Pump(220);
                Check(Same(ColorOf(surface), original), "Hover exit did not restore the base color.");
                surface.ClearValue(Motion.BackgroundProperty);
            }
            // Programmatic navigation/changelog colors flow through the same template binding.
            var target = Color.FromRgb(49, 73, 105);
            button.Background = new SolidColorBrush(target); Pump(220);
            Check(Same(ColorOf(Part<Border>(button, "Border")), target), "Navigation color binding was lost.");
            Console.WriteLine($"MOTION PASS {checks}: interpolation, reversal, rapid input, presets, disabled, checkbox/radio, hover, isolation; Windows animations={moving}");
        }
        finally { testWindow.Close(); }
    }
}
