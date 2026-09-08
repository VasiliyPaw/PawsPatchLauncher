using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;

namespace PawsPatchLauncher;

/// <summary>A track click starts the same continuous gesture as a thumb drag.</summary>
public sealed class DragAnywhereSlider : Slider
{
    private bool _trackDragging;
    private Track? Track => GetTemplateChild("PART_Track") as Track;

    protected override void OnPreviewMouseLeftButtonDown(MouseButtonEventArgs e)
    {
        if (Track is not { } track || track.Thumb?.IsMouseOver == true)
        {
            base.OnPreviewMouseLeftButtonDown(e); // Keep native thumb drag and keyboard behavior.
            return;
        }
        Focus();
        if (CaptureMouse())
        {
            _trackDragging = true;
            MoveTo(e.GetPosition(track));
            e.Handled = true;
        }
        else base.OnPreviewMouseLeftButtonDown(e);
    }

    protected override void OnPreviewMouseMove(MouseEventArgs e)
    {
        if (_trackDragging)
        {
            if (e.LeftButton == MouseButtonState.Pressed && Track is { } track) MoveTo(e.GetPosition(track));
            else EndTrackDrag();
            e.Handled = true;
        }
        base.OnPreviewMouseMove(e);
    }

    protected override void OnPreviewMouseLeftButtonUp(MouseButtonEventArgs e)
    {
        if (_trackDragging) { EndTrackDrag(); e.Handled = true; }
        base.OnPreviewMouseLeftButtonUp(e);
    }

    protected override void OnLostMouseCapture(MouseEventArgs e)
    {
        _trackDragging = false;
        base.OnLostMouseCapture(e);
    }

    private void EndTrackDrag()
    {
        _trackDragging = false;
        if (IsMouseCaptured) ReleaseMouseCapture();
    }

    private void MoveTo(Point position)
    {
        if (Track is not { } track) return;
        // Derive from absolute geometry, not the last arranged thumb position.
        // Several mouse moves can arrive before WPF has laid out the previous value.
        var thumbWidth = track.Thumb?.ActualWidth ?? 0;
        var travel = track.ActualWidth - thumbWidth;
        if (travel <= 0) return;
        var fraction = (position.X - thumbWidth / 2) / travel;
        if (track.IsDirectionReversed) fraction = 1 - fraction;
        var value = Minimum + fraction * (Maximum - Minimum);
        if (!double.IsFinite(value)) return;
        if (IsSnapToTickEnabled && TickFrequency > 0)
            value = Minimum + Math.Round((value - Minimum) / TickFrequency) * TickFrequency;
        SetCurrentValue(ValueProperty, Math.Clamp(value, Minimum, Maximum));
    }
}
