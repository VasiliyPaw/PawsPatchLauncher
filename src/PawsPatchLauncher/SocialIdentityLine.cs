using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

/// <summary>Aligns username and trusted badge; wraps the badge on narrow chat lists.</summary>
public sealed class SocialIdentityLine : Panel
{
    private bool _wrap;
    private const double Gap=6;
    protected override Size MeasureOverride(Size available)
    {
        if(Children.Count!=2)return new Size();
        var name=Children[0];var badge=Children[1];
        name.Measure(new Size(double.PositiveInfinity,double.PositiveInfinity));
        var fullName=name.DesiredSize.Width;
        badge.Measure(new Size(available.Width,double.PositiveInfinity));
        var badgeWidth=badge.DesiredSize.Width;
        _wrap=fullName+Gap+badgeWidth>available.Width;
        name.Measure(new Size(_wrap?available.Width:Math.Max(0,available.Width-badgeWidth-Gap),double.PositiveInfinity));
        return new Size(_wrap?Math.Max(name.DesiredSize.Width,badgeWidth):name.DesiredSize.Width+Gap+badgeWidth,
            _wrap?name.DesiredSize.Height+3+badge.DesiredSize.Height:Math.Max(name.DesiredSize.Height,badge.DesiredSize.Height));
    }
    protected override Size ArrangeOverride(Size size)
    {
        if(Children.Count!=2)return size;
        var name=Children[0];var badge=Children[1];var b=badge.DesiredSize;
        if(_wrap)
        {
            name.Arrange(new Rect(0,0,size.Width,name.DesiredSize.Height));
            badge.Arrange(new Rect(0,name.DesiredSize.Height+3,Math.Min(size.Width,b.Width),b.Height));
        }
        else
        {
            var nameWidth=Math.Max(0,size.Width-b.Width-Gap);
            name.Arrange(new Rect(0,(size.Height-name.DesiredSize.Height)/2,nameWidth,name.DesiredSize.Height));
            badge.Arrange(new Rect(nameWidth+Gap,(size.Height-b.Height)/2,Math.Min(size.Width,b.Width),b.Height));
        }
        return size;
    }
}
