using System.Windows;
using System.Windows.Controls.Primitives;
using System.Windows.Media.Animation;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private DoubleAnimation? _progressAnimation;
    private double _progressTarget;

    private void InitializeProgressMotion()
    {
        OperationProgress.IsVisibleChanged+=(_,_)=>{if(!OperationProgress.IsVisible)StopProgressAnimation();};
        OperationProgress.Unloaded+=(_,_)=>StopProgressAnimation();
        Closed+=(_,_)=>StopProgressAnimation();
    }

    private void StopProgressAnimation()
    {
        _progressAnimation=null;
        OperationProgress.BeginAnimation(RangeBase.ValueProperty,null);
        OperationProgress.Value=_progressTarget;
    }

    private void SetOperationProgress(double value,bool animate=true)
    {
        value=double.IsFinite(value)?Math.Clamp(value,OperationProgress.Minimum,OperationProgress.Maximum):OperationProgress.Minimum;
        if(animate&&Math.Abs(value-_progressTarget)<.0001)return;
        var from=OperationProgress.Value;
        StopProgressAnimation();
        _progressTarget=value;
        OperationProgress.Value=value;
        // Resets/retries, hidden windows and reduced motion take effect immediately.
        if(!animate||!OperationProgress.IsVisible||!OperationProgress.IsLoaded||OperationProgress.IsIndeterminate
            ||!SystemParameters.ClientAreaAnimation||value<=from)return;
        // Keep the displayed base at the current position until WPF's first
        // animation tick; setting it to the target can flash ahead on retarget.
        OperationProgress.Value=from;
        var animation=new DoubleAnimation(from,value,TimeSpan.FromMilliseconds(220))
        {
            EasingFunction=new CubicEase{EasingMode=EasingMode.EaseOut},
            FillBehavior=FillBehavior.HoldEnd
        };
        _progressAnimation=animation;
        animation.Completed+=(_,_)=>{if(ReferenceEquals(_progressAnimation,animation))StopProgressAnimation();};
        OperationProgress.BeginAnimation(RangeBase.ValueProperty,animation,HandoffBehavior.SnapshotAndReplace);
    }

    private void SetOperationIndeterminate(bool indeterminate)
    {
        if(indeterminate)StopProgressAnimation();
        OperationProgress.IsIndeterminate=indeterminate;
    }
}
