using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Media3D;

namespace PawsPatchLauncher;

// A dropdown/context menu owns wheel input until it closes. WPF mouse capture
// can route an outside wheel to its anchor inside a scrolling page.
public static class PopupScrollIsolation
{
    public static readonly DependencyProperty EnabledProperty = DependencyProperty.RegisterAttached(
        "Enabled", typeof(bool), typeof(PopupScrollIsolation), new PropertyMetadata(false, EnabledChanged));
    private static readonly DependencyProperty StateProperty = DependencyProperty.RegisterAttached(
        "State", typeof(State), typeof(PopupScrollIsolation));
    private static readonly DependencyProperty OwnerProperty = DependencyProperty.RegisterAttached(
        "Owner", typeof(Owner), typeof(PopupScrollIsolation));
    private static readonly DependencyProperty OwnerWindowProperty = DependencyProperty.RegisterAttached(
        "OwnerWindow", typeof(Window), typeof(PopupScrollIsolation),
        new FrameworkPropertyMetadata(null, FrameworkPropertyMetadataOptions.Inherits));
    public static bool GetEnabled(DependencyObject value) => (bool)value.GetValue(EnabledProperty);
    public static void SetEnabled(DependencyObject value, bool enabled) => value.SetValue(EnabledProperty, enabled);

    private static void EnabledChanged(DependencyObject value, DependencyPropertyChangedEventArgs args)
    {
        if (value is not Popup and not ContextMenu) return;
        (value.GetValue(StateProperty) as State)?.Dispose();
        value.SetValue(StateProperty, (bool)args.NewValue ? new State((FrameworkElement)value) : null);
    }
    private static bool Contains(DependencyObject root, DependencyObject? source)
    {
        for (var node = source; node is not null;)
        {
            if (ReferenceEquals(node, root)) return true;
            node = node is Visual or Visual3D ? VisualTreeHelper.GetParent(node)
                : node is FrameworkContentElement content ? content.Parent : LogicalTreeHelper.GetParent(node);
        }
        return false;
    }
    private sealed class Owner(Window window)
    {
        private readonly List<State> _open = [];
        public void Add(State state)
        {
            if (_open.Count == 0)
            {
                window.PreviewMouseWheel += Wheel;
                window.Closed += Closed;
            }
            _open.Add(state);
            SmoothScroll.StopAnimations(window);
        }
        public void Remove(State state)
        {
            _open.Remove(state);
            if (_open.Count != 0) return;
            window.PreviewMouseWheel -= Wheel;
            window.Closed -= Closed;
        }
        private void Wheel(object sender, MouseWheelEventArgs args)
        {
            if (_open.LastOrDefault()?.Root is { } root && !Contains(root, args.OriginalSource as DependencyObject))
                args.Handled = true;
        }
        private void Closed(object? sender, EventArgs args)
        {
            foreach (var state in _open.ToArray()) state.Close();
        }
    }
    private sealed class State
    {
        private readonly FrameworkElement _element;
        private Owner? _owner;
        public UIElement? Root { get; private set; }
        public State(FrameworkElement element)
        {
            _element = element;
            if (element is Popup popup) { popup.Opened += Opened; popup.Closed += Closed; }
            if (element is ContextMenu menu) { menu.Opened += Opened; menu.Closed += Closed; }
            element.Unloaded += Closed;
        }
        private void Opened(object? sender, EventArgs args)
        {
            Close();
            var target = _element is Popup popup ? popup.PlacementTarget ?? popup.TemplatedParent as UIElement
                : ((ContextMenu)_element).PlacementTarget;
            if (target is null) return;
            var window = Window.GetWindow(target) ?? target.GetValue(OwnerWindowProperty) as Window;
            Root = _element is Popup p ? p.Child : _element;
            if (window is null || Root is null) { Root = null; return; }
            _owner = window.GetValue(OwnerProperty) as Owner;
            if (_owner is null) window.SetValue(OwnerProperty, _owner = new Owner(window));
            Root.SetValue(OwnerWindowProperty, window);
            Root.AddHandler(Mouse.MouseWheelEvent, new MouseWheelEventHandler(Boundary), true);
            _owner.Add(this);
        }
        // An exhausted/short list must not hand its remaining wheel gesture to
        // the anchor's page through the popup's logical event route.
        private static void Boundary(object sender, MouseWheelEventArgs args) => args.Handled = true;
        private void Closed(object? sender, EventArgs args) => Close();
        public void Close()
        {
            _owner?.Remove(this); _owner = null;
            if (Root is not null)
            {
                Root.RemoveHandler(Mouse.MouseWheelEvent, new MouseWheelEventHandler(Boundary));
                Root.ClearValue(OwnerWindowProperty);
                Root = null;
            }
        }
        public void Dispose()
        {
            Close();
            if (_element is Popup popup) { popup.Opened -= Opened; popup.Closed -= Closed; }
            if (_element is ContextMenu menu) { menu.Opened -= Opened; menu.Closed -= Closed; }
            _element.Unloaded -= Closed;
        }
    }
}
