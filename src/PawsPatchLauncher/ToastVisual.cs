using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Media;

namespace PawsPatchLauncher;

internal sealed record ToastVisual(Border Panel, TranslateTransform Slide, LauncherIcon Icon, TextBlock Text,
    Button Close, Border Progress, ScaleTransform Scale)
{
    internal static ToastVisual Create(FrameworkElement owner)
    {
        var slide=new TranslateTransform();var scale=new ScaleTransform(0,1);
        var icon=new LauncherIcon {Kind=IconKind.Check};
        var text=new TextBlock {FontSize=13,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(6,0,14,0),VerticalAlignment=VerticalAlignment.Center};
        AutomationProperties.SetLiveSetting(text,AutomationLiveSetting.Polite);
        var close=new Button {Style=(Style)owner.FindResource("TitleButton"),Padding=new Thickness(0),Width=26,Height=28,
            VerticalAlignment=VerticalAlignment.Center,Content=new LauncherIcon {Kind=IconKind.Close,Width=16,Height=16}};
        var line=new Grid {Margin=new Thickness(16,12,16,12)};
        line.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(28)});
        line.ColumnDefinitions.Add(new ColumnDefinition());line.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(28)});
        line.Children.Add(icon);Grid.SetColumn(text,1);line.Children.Add(text);Grid.SetColumn(close,2);line.Children.Add(close);
        var progress=new Border {CornerRadius=new CornerRadius(1),Margin=new Thickness(9,0,9,0),RenderTransformOrigin=new Point(0,.5),RenderTransform=scale};
        var grid=new Grid();grid.RowDefinitions.Add(new RowDefinition());grid.RowDefinitions.Add(new RowDefinition {Height=new GridLength(3)});
        grid.Children.Add(line);Grid.SetRow(progress,1);grid.Children.Add(progress);
        var panel=new Border {BorderThickness=new Thickness(1),CornerRadius=new CornerRadius(10),MinWidth=300,MaxWidth=580,
            Margin=new Thickness(0,0,0,8),RenderTransform=slide,Child=grid};
        return new(panel,slide,icon,text,close,progress,scale);
    }
}
