using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;

namespace PawsPatchLauncher;

/// <summary>One retargetable batch for the list; never queues moves or animates layout sizes.</summary>
public sealed class ChatListMotion
{
    private readonly Panel _panel;
    private readonly DispatcherTimer _finish;
    private readonly List<(FrameworkElement Row,Transform Original,TranslateTransform Offset,int Z,double Opacity)> _active=[];
    public bool IsAnimating=>_active.Count>0;
    public ChatListMotion(Panel panel)
    {
        _panel=panel;
        _finish=new DispatcherTimer(DispatcherPriority.Render,panel.Dispatcher){Interval=TimeSpan.FromMilliseconds(360)};
        _finish.Tick+=(_,_)=>Stop();
        panel.Unloaded+=(_,_)=>Stop();
        panel.IsVisibleChanged+=(_,_)=>{if(!panel.IsVisible)Stop();};
    }
    public void Stop()
    {
        _finish.Stop();
        foreach(var (row,original,offset,z,opacity) in _active)
        {
            offset.BeginAnimation(TranslateTransform.XProperty,null);
            offset.BeginAnimation(TranslateTransform.YProperty,null);
            row.BeginAnimation(UIElement.OpacityProperty,null);
            row.Opacity=opacity; row.RenderTransform=original; Panel.SetZIndex(row,z);
        }
        _active.Clear();
    }
    public void Arrange(IReadOnlyList<FrameworkElement> ordered,bool animate)
    {
        var current=_panel.Children.OfType<FrameworkElement>().ToArray();
        if(current.SequenceEqual(ordered)) { if(!animate)Stop(); return; }
        // Capture current on-screen positions before stopping a previous transition.
        var before=current.ToDictionary(row=>row,row=>(Point:row.TranslatePoint(new Point(),_panel),Opacity:row.Opacity));
        Stop();
        foreach(var row in current.Where(row=>!ordered.Contains(row)))_panel.Children.Remove(row);
        for(var i=0;i<ordered.Count;i++)
        {
            var row=ordered[i];
            if(i<_panel.Children.Count&&ReferenceEquals(_panel.Children[i],row))continue;
            _panel.Children.Remove(row); _panel.Children.Insert(i,row);
        }
        _panel.UpdateLayout();
        if(!animate||!SystemParameters.ClientAreaAnimation||!_panel.IsVisible||current.Length==0||
            Window.GetWindow(_panel)?.WindowState==WindowState.Minimized)return;
        var ease=new CubicEase{EasingMode=EasingMode.EaseOut};
        foreach(var row in ordered)
        {
            if(row.ActualHeight<=0)continue;
            var position=row.TranslatePoint(new Point(),_panel);
            var existed=before.TryGetValue(row,out var prior);
            var dy=existed?prior.Point.Y-position.Y:0;
            var dx=existed?prior.Point.X-position.X:24;
            if(existed&&Math.Abs(dy)<.1&&Math.Abs(dx)<.1)continue;
            var original=row.RenderTransform; var offset=new TranslateTransform(dx,dy);
            var group=new TransformGroup();group.Children.Add(original);group.Children.Add(offset);
            var z=Panel.GetZIndex(row); _active.Add((row,original,offset,z,row.Opacity)); row.RenderTransform=group;
            if(dy>0)Panel.SetZIndex(row,10);
            offset.BeginAnimation(TranslateTransform.YProperty,new DoubleAnimation(dy,0,TimeSpan.FromMilliseconds(320)){EasingFunction=ease,FillBehavior=FillBehavior.HoldEnd});
            // A small side arc separates the promoted chat from the rows making room below.
            var horizontal=new DoubleAnimationUsingKeyFrames{FillBehavior=FillBehavior.HoldEnd};
            horizontal.KeyFrames.Add(new LinearDoubleKeyFrame(dx,KeyTime.FromTimeSpan(TimeSpan.Zero)));
            horizontal.KeyFrames.Add(new EasingDoubleKeyFrame(dy>0?18:0,KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(100)),ease));
            horizontal.KeyFrames.Add(new EasingDoubleKeyFrame(0,KeyTime.FromTimeSpan(TimeSpan.FromMilliseconds(320)),ease));
            offset.BeginAnimation(TranslateTransform.XProperty,horizontal);
            row.Opacity=existed?prior.Opacity:.55;
            row.BeginAnimation(UIElement.OpacityProperty,new DoubleAnimation(row.Opacity,1,TimeSpan.FromMilliseconds(220)){EasingFunction=ease,FillBehavior=FillBehavior.HoldEnd});
        }
        _panel.UpdateLayout();
        if(_active.Count>0)_finish.Start();
    }
}
