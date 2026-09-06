using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Animation;

namespace PawsPatchLauncher;

/// <summary>Transient decoration only: no layout, input, settings or shared-brush mutations.</summary>
public sealed class CardHighlight : Adorner
{
    private readonly AdornerLayer _layer;
    private int _version;
    private CardHighlight(Border card, AdornerLayer layer) : base(card)
    {
        _layer = layer;
        IsHitTestVisible = false;
        Opacity = 0;
        card.Unloaded += OnUnloaded;
    }

    public static void Pulse(Border card)
    {
        if (!SystemParameters.ClientAreaAnimation || !card.IsVisible || card.ActualWidth <= 0 || card.ActualHeight <= 0) return;
        var layer = AdornerLayer.GetAdornerLayer(card);
        if (layer is null) return;
        var pulse = layer.GetAdorners(card)?.OfType<CardHighlight>().FirstOrDefault();
        if (pulse is null) { pulse = new CardHighlight(card, layer); layer.Add(pulse); }
        pulse.Restart();
    }

    private void Restart()
    {
        var version = ++_version;
        var animation = new DoubleAnimationUsingKeyFrames { FillBehavior = FillBehavior.Stop };
        animation.KeyFrames.Add(new LinearDoubleKeyFrame(Opacity, KeyTime.FromTimeSpan(TimeSpan.Zero)));
        animation.KeyFrames.Add(new EasingDoubleKeyFrame(1, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(100)), new CubicEase { EasingMode = EasingMode.EaseOut }));
        animation.KeyFrames.Add(new EasingDoubleKeyFrame(0, KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(700)), new CubicEase { EasingMode = EasingMode.EaseInOut }));
        animation.Completed += (_, _) => { if (version == _version) Remove(); };
        BeginAnimation(OpacityProperty, animation, HandoffBehavior.SnapshotAndReplace);
    }

    private void OnUnloaded(object sender, RoutedEventArgs e) => Remove();
    private void Remove()
    {
        _version++;
        BeginAnimation(OpacityProperty, null);
        ((FrameworkElement)AdornedElement).Unloaded -= OnUnloaded;
        _layer.Remove(this);
    }

    protected override void OnRender(DrawingContext dc)
    {
        var card = (Border)AdornedElement;
        var size = card.RenderSize;
        if (size.Width < 4 || size.Height < 4) return;
        var radius = Math.Max(0, card.CornerRadius.TopLeft - 1);
        dc.DrawRoundedRectangle(new SolidColorBrush(Color.FromArgb(14, 215, 175, 86)),
            new Pen(new SolidColorBrush(Color.FromArgb(175, 215, 175, 86)), 1),
            new Rect(1.5, 1.5, size.Width - 3, size.Height - 3), radius, radius);
    }
}
