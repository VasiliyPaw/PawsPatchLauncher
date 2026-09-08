using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;

namespace PawsPatchLauncher;

/// <summary>One-shot arrival effects. No layout animation, shared-brush mutation or idle clock.</summary>
public static class ArrivalMotion
{
    private static readonly DependencyProperty CleanupProperty = DependencyProperty.RegisterAttached("Cleanup", typeof(Action), typeof(ArrivalMotion));
    public static bool IsRunning(FrameworkElement view) => view.GetValue(CleanupProperty) is Action;
    private static bool CanAnimate(FrameworkElement view) => SystemParameters.ClientAreaAnimation && view.IsVisible
        && view.ActualHeight > 0 && view.ActualWidth > 0 && Window.GetWindow(view)?.WindowState != WindowState.Minimized;

    public static void Enter(FrameworkElement view)
    {
        if (!CanAnimate(view)) return;
        (view.GetValue(CleanupProperty) as Action)?.Invoke();
        var target = view.Opacity; var original = view.RenderTransform;
        var offset = new TranslateTransform();
        var group = new TransformGroup(); group.Children.Add(original); group.Children.Add(offset);
        view.RenderTransform = group;
        var animation = new DoubleAnimation(target * .68, target, TimeSpan.FromMilliseconds(180))
        { EasingFunction = new CubicEase { EasingMode=EasingMode.EaseOut }, FillBehavior=FillBehavior.Stop };
        view.BeginAnimation(UIElement.OpacityProperty, animation);
        offset.BeginAnimation(TranslateTransform.YProperty, new DoubleAnimation(4,0,animation.Duration)
        { EasingFunction=animation.EasingFunction, FillBehavior=FillBehavior.Stop });
        FinishAfter(view, 230, () =>
        {
            view.BeginAnimation(UIElement.OpacityProperty,null);
            offset.BeginAnimation(TranslateTransform.YProperty,null);
            if (ReferenceEquals(view.RenderTransform,group)) view.RenderTransform=original;
        });
    }

    public static void Pulse(Border badge)
    {
        if (!CanAnimate(badge) || badge.Background is not SolidColorBrush) return;
        (badge.GetValue(CleanupProperty) as Action)?.Invoke();
        var original = (SolidColorBrush)badge.Background;
        var brush = original.CloneCurrentValue(); badge.Background=brush;
        var color = brush.Color;
        byte Brighter(byte value) => (byte)Math.Min(255, value + 45);
        brush.BeginAnimation(SolidColorBrush.ColorProperty, new ColorAnimation(color,
            Color.FromArgb(color.A,Brighter(color.R),Brighter(color.G),Brighter(color.B)),TimeSpan.FromMilliseconds(150))
        { AutoReverse=true, FillBehavior=FillBehavior.Stop, EasingFunction=new SineEase {EasingMode=EasingMode.EaseInOut} });
        FinishAfter(badge, 350, () =>
        {
            brush.BeginAnimation(SolidColorBrush.ColorProperty,null);
            if (ReferenceEquals(badge.Background,brush)) badge.Background=original;
        });
    }

    private static void FinishAfter(FrameworkElement view, int milliseconds, Action cleanup)
    {
        var timer = new DispatcherTimer(DispatcherPriority.Background,view.Dispatcher) { Interval=TimeSpan.FromMilliseconds(milliseconds) };
        RoutedEventHandler? unloaded=null;
        void Finish()
        {
            timer.Stop(); view.Unloaded-=unloaded; view.ClearValue(CleanupProperty); cleanup();
        }
        unloaded=(_,_)=>Finish(); view.Unloaded+=unloaded;
        view.SetValue(CleanupProperty,(Action)Finish);
        timer.Tick+=(_,_)=>Finish(); timer.Start();
    }
}
