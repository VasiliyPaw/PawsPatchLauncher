using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;

namespace PawsPatchLauncher;

/// <summary>Presentation-only transitions. Never animates a setting or delays a command.</summary>
public static class Motion
{
    public static readonly DependencyProperty BackgroundProperty = BrushProperty("Background", Border.BackgroundProperty);
    public static readonly DependencyProperty BorderBrushProperty = BrushProperty("BorderBrush", Border.BorderBrushProperty);
    public static readonly DependencyProperty FillProperty = BrushProperty("Fill", Shape.FillProperty);
    public static readonly DependencyProperty ForegroundProperty = BrushProperty("Foreground", TextElement.ForegroundProperty);
    public static readonly DependencyProperty OffsetXProperty = DependencyProperty.RegisterAttached("OffsetX", typeof(double), typeof(Motion), new PropertyMetadata(0d, OffsetChanged));
    public static readonly DependencyProperty OpacityProperty = DependencyProperty.RegisterAttached("Opacity", typeof(double), typeof(Motion), new PropertyMetadata(1d, OpacityChanged));
    public static readonly DependencyProperty HoverBackgroundProperty = DependencyProperty.RegisterAttached("HoverBackground", typeof(Brush), typeof(Motion));
    public static readonly DependencyProperty PressedBackgroundProperty = DependencyProperty.RegisterAttached("PressedBackground", typeof(Brush), typeof(Motion));
    private static readonly DependencyProperty TransitionVersionProperty = DependencyProperty.RegisterAttached("TransitionVersion", typeof(int), typeof(Motion), new PropertyMetadata(0));

    public static void Reveal(FrameworkElement view)
    {
        view.SetValue(TransitionVersionProperty, (int)view.GetValue(TransitionVersionProperty) + 1);
        var from = view.Opacity < 0.999 ? view.Opacity : 0.55;
        view.BeginAnimation(UIElement.OpacityProperty, null);
        view.Visibility = Visibility.Visible;
        view.Opacity = 1;
        if (Animate(view))
        {
            view.Opacity = from;
            view.BeginAnimation(UIElement.OpacityProperty, Transition(from, 1, 160), HandoffBehavior.SnapshotAndReplace);
        }
    }

    public static void Hide(FrameworkElement view)
    {
        var version = (int)view.GetValue(TransitionVersionProperty) + 1;
        view.SetValue(TransitionVersionProperty, version);
        void Finish()
        {
            if ((int)view.GetValue(TransitionVersionProperty) != version) return;
            view.Visibility = Visibility.Collapsed;
            view.BeginAnimation(UIElement.OpacityProperty, null);
            view.Opacity = 1;
        }
        if (!Animate(view)) { Finish(); return; }
        var animation = Transition(view.Opacity, 0, 120);
        animation.Completed += (_, _) => Finish();
        view.BeginAnimation(UIElement.OpacityProperty, animation, HandoffBehavior.SnapshotAndReplace);
    }

    public static Brush? GetBackground(DependencyObject o) => (Brush?)o.GetValue(BackgroundProperty);
    public static void SetBackground(DependencyObject o, Brush? value) => o.SetValue(BackgroundProperty, value);
    public static Brush? GetBorderBrush(DependencyObject o) => (Brush?)o.GetValue(BorderBrushProperty);
    public static void SetBorderBrush(DependencyObject o, Brush? value) => o.SetValue(BorderBrushProperty, value);
    public static Brush? GetFill(DependencyObject o) => (Brush?)o.GetValue(FillProperty);
    public static void SetFill(DependencyObject o, Brush? value) => o.SetValue(FillProperty, value);
    public static Brush? GetForeground(DependencyObject o) => (Brush?)o.GetValue(ForegroundProperty);
    public static void SetForeground(DependencyObject o, Brush? value) => o.SetValue(ForegroundProperty, value);
    public static double GetOffsetX(DependencyObject o) => (double)o.GetValue(OffsetXProperty);
    public static void SetOffsetX(DependencyObject o, double value) => o.SetValue(OffsetXProperty, value);
    public static double GetOpacity(DependencyObject o) => (double)o.GetValue(OpacityProperty);
    public static void SetOpacity(DependencyObject o, double value) => o.SetValue(OpacityProperty, value);
    public static Brush? GetHoverBackground(DependencyObject o) => (Brush?)o.GetValue(HoverBackgroundProperty);
    public static void SetHoverBackground(DependencyObject o, Brush? value) => o.SetValue(HoverBackgroundProperty, value);
    public static Brush? GetPressedBackground(DependencyObject o) => (Brush?)o.GetValue(PressedBackgroundProperty);
    public static void SetPressedBackground(DependencyObject o, Brush? value) => o.SetValue(PressedBackgroundProperty, value);

    private static DependencyProperty BrushProperty(string name, DependencyProperty visualProperty)
        => DependencyProperty.RegisterAttached(name, typeof(Brush), typeof(Motion),
            new PropertyMetadata(null, (o, e) => ChangeBrush((FrameworkElement)o, visualProperty, (Brush?)e.NewValue)));

    // The first layout renders its final state immediately (including preselected/disabled controls).
    // Honor Windows' reduced-animation preference; only already measured controls can animate.
    private static bool Animate(FrameworkElement view) => SystemParameters.ClientAreaAnimation
        && view.Visibility == Visibility.Visible && view.ActualWidth > 0 && view.ActualHeight > 0;

    private static void ChangeBrush(FrameworkElement view, DependencyProperty property, Brush? target)
    {
        var current = view.GetValue(property) as SolidColorBrush;
        if (target is not SolidColorBrush color)
        {
            view.SetValue(property, target?.CloneCurrentValue());
            return;
        }
        // Always own our brush: never mutate a shared/frozen theme resource or another control.
        var animate = current is not null && !SameColor(current.Color, color.Color) && Animate(view);
        // Keep the displayed starting value until WPF's next animation frame.
        var brush = new SolidColorBrush(animate ? current!.Color : color.Color) { Opacity = color.Opacity };
        view.SetValue(property, brush);
        if (animate)
            brush.BeginAnimation(SolidColorBrush.ColorProperty, new ColorAnimation(current!.Color, color.Color, TimeSpan.FromMilliseconds(160))
            {
                EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut },
                FillBehavior = FillBehavior.HoldEnd
            }, HandoffBehavior.SnapshotAndReplace);
    }

    private static void OffsetChanged(DependencyObject o, DependencyPropertyChangedEventArgs e)
    {
        var view = (FrameworkElement)o;
        var from = (view.RenderTransform as TranslateTransform)?.X ?? 0;
        var to = (double)e.NewValue;
        var animate = Animate(view) && Math.Abs(from - to) > 0.001;
        var transform = new TranslateTransform(animate ? from : to, 0);
        view.RenderTransform = transform;
        if (animate)
            transform.BeginAnimation(TranslateTransform.XProperty, Transition(from, to, 210), HandoffBehavior.SnapshotAndReplace);
    }

    private static void OpacityChanged(DependencyObject o, DependencyPropertyChangedEventArgs e)
    {
        var view = (FrameworkElement)o;
        var from = view.Opacity;
        var to = (double)e.NewValue;
        var animate = Animate(view) && Math.Abs(from - to) > 0.001;
        view.BeginAnimation(UIElement.OpacityProperty, null);
        view.Opacity = animate ? from : to;
        if (animate)
            view.BeginAnimation(UIElement.OpacityProperty, Transition(from, to, 160), HandoffBehavior.SnapshotAndReplace);
    }

    private static DoubleAnimation Transition(double from, double to, int milliseconds) => new(from, to, TimeSpan.FromMilliseconds(milliseconds))
    {
        EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut },
        FillBehavior = FillBehavior.HoldEnd
    };

    private static bool SameColor(Color left, Color right) => left.A == right.A && left.R == right.R && left.G == right.G && left.B == right.B;
}
