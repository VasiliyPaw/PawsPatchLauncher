using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media.Animation;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private DoubleAnimation? _progressAnimation;
    private double _progressTarget;
    private readonly Dictionary<TextBlock, DoubleAnimation> _operationTextAnimations = [];
    private bool _operationDetailsExpanded;
    private double _operationDetailsHeight;
    private DoubleAnimation? _operationDetailsAnimation;

    private void OperationDetails_Click(object sender, RoutedEventArgs e)
    {
        _operationDetailsExpanded = !_operationDetailsExpanded;
        RefreshOperationDetails(OperationWorkDetails.Visibility == Visibility.Visible);
    }

    private void RefreshOperationDetails(bool working)
    {
        OperationDetailsButton.Visibility = TransferSummaryText.Visibility = working ? Visibility.Visible : Visibility.Collapsed;
        OperationText.Visibility = working ? Visibility.Collapsed : Visibility.Visible;
        RefreshTransferSummary();
        var arrowAngle = _operationDetailsExpanded ? 180d : 0d;
        if ((double)OperationDetailsChevronRotation.GetAnimationBaseValue(RotateTransform.AngleProperty) != arrowAngle)
        {
            var fromAngle = OperationDetailsChevronRotation.Angle;
            OperationDetailsChevronRotation.BeginAnimation(RotateTransform.AngleProperty, null);
            OperationDetailsChevronRotation.Angle = arrowAngle;
            if (working && IsLoaded && SystemParameters.ClientAreaAnimation)
                OperationDetailsChevronRotation.BeginAnimation(RotateTransform.AngleProperty,
                    new DoubleAnimation(fromAngle, arrowAngle, TimeSpan.FromMilliseconds(180))
                    { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }, FillBehavior = FillBehavior.Stop });
        }
        OperationDetailsButton.ToolTip = _operationDetailsExpanded ? T("Свернуть подробности", "Hide details") : T("Подробнее о загрузке", "Download details");
        System.Windows.Automation.AutomationProperties.SetName(OperationDetailsButton, (string)OperationDetailsButton.ToolTip);
        var target = working && _operationDetailsExpanded ? 84d : 0d;
        if (_operationDetailsHeight == target) return;
        _operationDetailsHeight = target;
        var from = OperationExpandedDetails.ActualHeight;
        OperationExpandedDetails.BeginAnimation(HeightProperty, null);
        _operationDetailsAnimation = null;
        OperationExpandedDetails.Height = target;
        if (!working || !IsLoaded || !SystemParameters.ClientAreaAnimation)
        {
            OperationExpandedDetails.Visibility = target > 0 ? Visibility.Visible : Visibility.Collapsed;
            return;
        }
        OperationExpandedDetails.Visibility = Visibility.Visible;
        var animation = new DoubleAnimation(from, target, TimeSpan.FromMilliseconds(220))
            { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } };
        _operationDetailsAnimation = animation;
        animation.Completed += (_, _) =>
        {
            if (!ReferenceEquals(_operationDetailsAnimation, animation)) return;
            OperationExpandedDetails.BeginAnimation(HeightProperty, null);
            OperationExpandedDetails.Height = target;
            OperationExpandedDetails.Visibility = target > 0 ? Visibility.Visible : Visibility.Collapsed;
            _operationDetailsAnimation = null;
        };
        OperationExpandedDetails.BeginAnimation(HeightProperty, animation);
    }

    private void RefreshTransferSummary()
    {
        TransferSummaryText.Text = _transferReceived is not long received ? OperationText.Text
            : _transferTotal is > 0 ? FormatBytes(received) + " / " + FormatBytes(_transferTotal.Value)
                + $" · {Math.Clamp(received * 100d / _transferTotal.Value, 0, 100):0}%"
            : FormatBytes(received);
    }

    private void InitializeProgressMotion()
    {
        OperationProgress.IsVisibleChanged+=(_,_)=>{if(!OperationProgress.IsVisible)StopProgressAnimation();};
        OperationProgress.Unloaded+=(_,_)=>StopProgressAnimation();
        Closed+=(_,_)=>{StopProgressAnimation();StopOperationTextAnimations();OperationExpandedDetails.BeginAnimation(HeightProperty,null);OperationDetailsChevronRotation.BeginAnimation(RotateTransform.AngleProperty,null);};
    }

    private void SetOperationCaption(string text)
    {
        if(OperationText.Text==text)return;
        OperationText.Text=text;
        FadeOperationText(OperationText);
    }

    private void SetTransferDetails(string text,bool phaseChanged=false)
    {
        var changed=TransferText.Text!=text;
        TransferText.Text=text;
        TransferText.ToolTip=text;
        TransferText.Visibility=Visibility.Visible;
        // Measurements update immediately; only phase labels ease in, without fading to blank.
        if(changed&&phaseChanged)FadeOperationText(TransferText);
    }

    private void FadeOperationText(TextBlock text)
    {
        var from=text.Opacity<1?text.Opacity:.86;
        text.BeginAnimation(OpacityProperty,null);
        text.Opacity=1;
        _operationTextAnimations.Remove(text);
        if(!text.IsLoaded||!text.IsVisible||!SystemParameters.ClientAreaAnimation)return;
        var animation=new DoubleAnimation(from,1,TimeSpan.FromMilliseconds(160))
        {EasingFunction=new CubicEase{EasingMode=EasingMode.EaseOut}};
        _operationTextAnimations[text]=animation;
        animation.Completed+=(_,_)=>
        {
            if(!_operationTextAnimations.TryGetValue(text,out var current)||!ReferenceEquals(current,animation))return;
            text.BeginAnimation(OpacityProperty,null);
            _operationTextAnimations.Remove(text);
        };
        text.BeginAnimation(OpacityProperty,animation,HandoffBehavior.SnapshotAndReplace);
    }

    private void StopOperationTextAnimations()
    {
        foreach(var text in _operationTextAnimations.Keys.ToArray())text.BeginAnimation(OpacityProperty,null);
        _operationTextAnimations.Clear();
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
