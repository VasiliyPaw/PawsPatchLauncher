using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;
using System.Windows.Threading;

namespace PawsPatchLauncher;

/// <summary>Presentation-only transitions. Never changes a setting or executes an operation.</summary>
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
    private static readonly DependencyProperty HideOperationProperty = DependencyProperty.RegisterAttached("HideOperation", typeof(HideOperation), typeof(Motion));
    private sealed class HideOperation
    {
        public readonly TaskCompletionSource<bool> Completion = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public Action? Cancel;
    }

    public static void Reveal(FrameworkElement view)
    {
        var from = view.Opacity < 0.999 ? view.Opacity : 0.55;
        (view.GetValue(HideOperationProperty) as HideOperation)?.Cancel?.Invoke();
        view.BeginAnimation(UIElement.OpacityProperty, null);
        view.Visibility = Visibility.Visible;
        view.Opacity = 1;
        if (Animate(view))
        {
            view.Opacity = from;
            view.BeginAnimation(UIElement.OpacityProperty, Transition(from, 1, 160), HandoffBehavior.SnapshotAndReplace);
        }
    }

    public static void RevealFromBottom(FrameworkElement view, TranslateTransform transform)
    {
        var from = IsHiding(view) ? transform.Y : 24;
        var fromX = transform.X;
        Reveal(view);
        transform.BeginAnimation(TranslateTransform.XProperty,null);transform.X=0;
        transform.BeginAnimation(TranslateTransform.YProperty, null);
        transform.Y = 0;
        if (Animate(view))
        {
            transform.X=fromX;
            if(Math.Abs(fromX)>.01)transform.BeginAnimation(TranslateTransform.XProperty,Transition(fromX,0,220),HandoffBehavior.SnapshotAndReplace);
            transform.Y = from;
            transform.BeginAnimation(TranslateTransform.YProperty, Transition(from, 0, 220), HandoffBehavior.SnapshotAndReplace);
        }
    }

    public static bool IsHiding(FrameworkElement view) => view.GetValue(HideOperationProperty) is HideOperation;
    public static void Hide(FrameworkElement view) => _ = HideAsync(view);
    public static void HideToBottom(FrameworkElement view, TranslateTransform transform) => _ = HideAsync(view, transform);
    public static Task<bool> HideToBottomAsync(FrameworkElement view, TranslateTransform transform) => HideAsync(view, transform);
    public static Task<bool> HideToRightAsync(FrameworkElement view, TranslateTransform transform) => HideAsync(view, transform, horizontal:true);

    public static void Reposition(FrameworkElement view,TranslateTransform transform,double from)
    {
        transform.BeginAnimation(TranslateTransform.YProperty,null);
        transform.Y=Animate(view)?from:0;
        if(Animate(view))transform.BeginAnimation(TranslateTransform.YProperty,Transition(from,0,220),HandoffBehavior.SnapshotAndReplace);
    }

    // Immediate teardown for account changes/removal, not user dismissal.
    public static void Collapse(FrameworkElement view)
    {
        (view.GetValue(HideOperationProperty) as HideOperation)?.Cancel?.Invoke();
        view.Visibility=Visibility.Collapsed;
        view.BeginAnimation(UIElement.OpacityProperty,null);view.Opacity=1;
    }

    public static Task<bool> HideAsync(FrameworkElement view) => HideAsync(view, null);

    private static Task<bool> HideAsync(FrameworkElement view, TranslateTransform? slide,bool horizontal=false)
    {
        if(view.GetValue(HideOperationProperty) is HideOperation pending)return pending.Completion.Task;
        if(!view.IsLoaded || !Animate(view))
        {
            Collapse(view);
            if(slide is not null)
            { slide.BeginAnimation(TranslateTransform.XProperty,null);slide.BeginAnimation(TranslateTransform.YProperty,null);slide.X=slide.Y=0; }
            return Task.FromResult(true);
        }
        var operation=new HideOperation();view.SetValue(HideOperationProperty,operation);
        var timer=new DispatcherTimer(DispatcherPriority.Background,view.Dispatcher) {Interval=TimeSpan.FromMilliseconds(250)};
        RoutedEventHandler? unloaded=null;
        void Finish(bool collapsed)
        {
            if(!ReferenceEquals(view.GetValue(HideOperationProperty),operation))return;
            timer.Stop();view.Unloaded-=unloaded;view.ClearValue(HideOperationProperty);
            var opacity=view.Opacity;
            if(slide is not null)
            {
                var offsetX=slide.X;var offsetY=slide.Y;
                slide.BeginAnimation(TranslateTransform.XProperty,null);slide.BeginAnimation(TranslateTransform.YProperty,null);
                slide.X=collapsed?0:offsetX;slide.Y=collapsed?0:offsetY;
            }
            if(collapsed)view.Visibility=Visibility.Collapsed;
            view.BeginAnimation(UIElement.OpacityProperty,null);view.Opacity=collapsed?1:opacity;
            operation.Completion.TrySetResult(collapsed);
        }
        operation.Cancel=()=>Finish(false);
        unloaded=(_,_)=>Finish(true);view.Unloaded+=unloaded;
        // The fallback also completes while minimized, when render clocks may stop.
        timer.Tick+=(_,_)=>Finish(true);timer.Start();
        var duration=slide is null?180:220;
        if(slide is not null)
        {
            var offsetX=slide.X;var offset=slide.Y;
            slide.BeginAnimation(TranslateTransform.XProperty,null);slide.X=offsetX;
            slide.BeginAnimation(TranslateTransform.YProperty,null);slide.Y=offset;
            slide.BeginAnimation(horizontal?TranslateTransform.XProperty:TranslateTransform.YProperty,
                Transition(horizontal?offsetX:offset,horizontal?48:24,duration),HandoffBehavior.SnapshotAndReplace);
        }
        var fromOpacity=view.Opacity;
        view.BeginAnimation(UIElement.OpacityProperty,null);view.Opacity=fromOpacity;
        var animation=Transition(fromOpacity,0,duration);
        animation.EasingFunction=new CubicEase {EasingMode=EasingMode.EaseInOut};
        animation.Completed+=(_,_)=>Finish(true);
        view.BeginAnimation(UIElement.OpacityProperty,animation,HandoffBehavior.SnapshotAndReplace);
        return operation.Completion.Task;
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
