using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Media3D;

namespace PawsPatchLauncher;

// Pixel scrolling only. Native thumb dragging, touch manipulation, caret navigation,
// logical/virtualized lists and application ScrollTo* calls keep their own semantics.
public static class SmoothScroll
{
    public static readonly DependencyProperty EnabledProperty = DependencyProperty.RegisterAttached(
        "Enabled", typeof(bool), typeof(SmoothScroll), new PropertyMetadata(false, EnabledChanged));
    private static readonly DependencyProperty StateProperty = DependencyProperty.RegisterAttached(
        "State", typeof(State), typeof(SmoothScroll));
    public static bool GetEnabled(DependencyObject o) => (bool)o.GetValue(EnabledProperty);
    public static void SetEnabled(DependencyObject o, bool value) => o.SetValue(EnabledProperty, value);
    public static bool IsAnimating(ScrollViewer view) => (view.GetValue(StateProperty) as State)?.Running == true;
    public static void ToBottom(ScrollViewer view)
    {
        if(view.GetValue(StateProperty) is State state)state.ToBottom();
        else view.ScrollToEnd();
    }

    private static void EnabledChanged(DependencyObject o, DependencyPropertyChangedEventArgs e)
    {
        if (o is not ScrollViewer view) return;
        if (view.GetValue(StateProperty) is State old) old.Dispose();
        view.SetValue(StateProperty, (bool)e.NewValue ? new State(view) : null);
    }
    private static DependencyObject? Parent(DependencyObject node) => node is Visual or Visual3D
        ? VisualTreeHelper.GetParent(node) : node is FrameworkContentElement content ? content.Parent : LogicalTreeHelper.GetParent(node);
    private static ScrollViewer? Nearest(DependencyObject? source)
    {
        for (var node=source; node is not null; node=Parent(node)) if (node is ScrollViewer view) return view;
        return null;
    }

    private sealed class State
    {
        private readonly ScrollViewer _view;
        private readonly Stopwatch _clock = new();
        private double _from, _target, _requested;
        private double _duration = 180;
        private bool _horizontal;
        private bool _followEnd;
        public bool Running { get; private set; }
        private double Current => _horizontal ? _view.HorizontalOffset : _view.VerticalOffset;
        private double Limit => _horizontal ? _view.ScrollableWidth : _view.ScrollableHeight;
        private double Viewport(bool horizontal) => horizontal ? _view.ViewportWidth : _view.ViewportHeight;

        public State(ScrollViewer view)
        {
            _view=view;
            view.PreviewMouseWheel+=Wheel;
            view.PreviewMouseDown+=MouseDown;
            view.PreviewKeyDown+=KeyDown;
            view.ScrollChanged+=Changed;
            view.IsVisibleChanged+=VisibilityChanged;
            view.Unloaded+=Unloaded;
            CommandManager.AddPreviewExecutedHandler(view, Command);
        }
        public void Dispose()
        {
            Stop();_view.PreviewMouseWheel-=Wheel;_view.PreviewMouseDown-=MouseDown;
            _view.PreviewKeyDown-=KeyDown;_view.ScrollChanged-=Changed;
            _view.IsVisibleChanged-=VisibilityChanged;_view.Unloaded-=Unloaded;
            CommandManager.RemovePreviewExecutedHandler(_view, Command);
        }
        private void Stop()
        {
            _followEnd=false;
            if (!Running) return;
            Running=false;_clock.Stop();CompositionTarget.Rendering-=Frame;
        }
        private void SetOffset(double offset)
        {
            _requested=Math.Clamp(offset, 0, Limit);
            if (_horizontal) _view.ScrollToHorizontalOffset(_requested); else _view.ScrollToVerticalOffset(_requested);
        }
        private void Scroll(double delta, bool horizontal)
        {
            _followEnd=false;
            _duration = 180;
            if (_view.CanContentScroll || delta==0) return;
            // Same-direction ticks accumulate, reversal responds immediately from the visible position.
            var previousTarget=Running && _horizontal==horizontal ? _target : double.NaN;
            if (Running && _horizontal!=horizontal) Stop();
            _horizontal=horizontal;
            var current=Current;
            var basis=!double.IsNaN(previousTarget) && Math.Sign(previousTarget-current)==Math.Sign(delta) ? previousTarget : current;
            _from=current;_target=Math.Clamp(basis+delta,0,Limit);_requested=current;
            if (!_view.IsLoaded || !_view.IsVisible || !SystemParameters.ClientAreaAnimation)
            { Stop();SetOffset(_target);return; }
            if (Math.Abs(_target-current)<0.1) { Stop();return; }
            _clock.Restart();
            if (!Running) { Running=true;CompositionTarget.Rendering+=Frame; }
        }
        public void ToBottom()
        {
            Stop();_horizontal=false;
            Scroll(_view.ScrollableHeight-_view.VerticalOffset,false);_duration=360;
            _followEnd=Running;
        }
        private void Frame(object? sender, EventArgs e)
        {
            if(!SystemParameters.ClientAreaAnimation) {SetOffset(_target);Stop();return;}
            var t=Math.Clamp(_clock.Elapsed.TotalMilliseconds/_duration,0,1);
            var eased=1-Math.Pow(1-t,3);
            SetOffset(_from+(_target-_from)*eased);
            if(t>=1)Stop();
        }
        private void Wheel(object sender, MouseWheelEventArgs e)
        {
            if(e.Handled || (Keyboard.Modifiers & (ModifierKeys.Control|ModifierKeys.Alt))!=0 || SystemParameters.WheelScrollLines==0)return;
            var horizontal=(Keyboard.Modifiers & ModifierKeys.Shift)!=0;
            // Only the innermost view with room in this direction consumes the gesture.
            ScrollViewer? destination=null;
            for(var node=e.OriginalSource as DependencyObject;node is not null;node=Parent(node))
                if(node is ScrollViewer candidate)
                {
                    var position=horizontal?candidate.HorizontalOffset:candidate.VerticalOffset;
                    var maximum=horizontal?candidate.ScrollableWidth:candidate.ScrollableHeight;
                    if(e.Delta<0 ? position<maximum-0.1 : position>0.1) { destination=candidate;break; }
                }
            if(!ReferenceEquals(destination,_view) || _view.CanContentScroll)return;
            var amount=SystemParameters.WheelScrollLines<0 ? Viewport(horizontal) : SystemParameters.WheelScrollLines*16d;
            e.Handled=true;Scroll(-e.Delta/120d*amount,horizontal);
        }
        private void Command(object sender, ExecutedRoutedEventArgs e)
        {
            if(e.Handled || _view.CanContentScroll || !ReferenceEquals(Nearest(e.OriginalSource as DependencyObject),_view))return;
            var command=e.Command;
            bool horizontal=command==ScrollBar.PageLeftCommand || command==ScrollBar.PageRightCommand
                || command==ScrollBar.LineLeftCommand || command==ScrollBar.LineRightCommand;
            double delta=command==ScrollBar.PageDownCommand ? Viewport(false) : command==ScrollBar.PageUpCommand ? -Viewport(false)
                : command==ScrollBar.PageRightCommand ? Viewport(true) : command==ScrollBar.PageLeftCommand ? -Viewport(true)
                : command==ScrollBar.LineDownCommand || command==ScrollBar.LineRightCommand ? 16
                : command==ScrollBar.LineUpCommand || command==ScrollBar.LineLeftCommand ? -16 : 0;
            if(delta==0)return;
            e.Handled=true;Scroll(delta,horizontal);
        }
        private void KeyDown(object sender, KeyEventArgs e)
        {
            Stop(); // Never fight the caret, keyboard focus, Home/End or a new selection.
            if(e.Handled || _view.CanContentScroll || !ReferenceEquals(e.OriginalSource,_view) || Keyboard.Modifiers!=ModifierKeys.None)return;
            double delta=e.Key==Key.PageDown ? Viewport(false) : e.Key==Key.PageUp ? -Viewport(false)
                : e.Key==Key.Down ? 16 : e.Key==Key.Up ? -16 : 0;
            if(delta!=0) { e.Handled=true;Scroll(delta,false); }
        }
        private void Changed(object sender, ScrollChangedEventArgs e)
        {
            if(!ReferenceEquals(e.OriginalSource,_view) || !Running)return;
            if(_followEnd && (e.ExtentHeightChange!=0 || e.ViewportHeightChange!=0))
            {
                // A decoded image or a newly laid out page may change the destination after a click.
                // Follow the new bottom; explicit input still cancels through Wheel/KeyDown/MouseDown.
                _from=Current;_target=Limit;_requested=Current;_clock.Restart();
                return;
            }
            if(e.ExtentHeightChange!=0 || e.ExtentWidthChange!=0 || e.ViewportHeightChange!=0 || e.ViewportWidthChange!=0
                || Math.Abs(Current-_requested)>1.5) Stop(); // Resize/content replacement or application navigation wins.
        }
        private void MouseDown(object sender, MouseButtonEventArgs e)=>Stop();
        private void Unloaded(object sender, RoutedEventArgs e)=>Stop();
        private void VisibilityChanged(object sender, DependencyPropertyChangedEventArgs e){if(!(bool)e.NewValue)Stop();}
    }
}
