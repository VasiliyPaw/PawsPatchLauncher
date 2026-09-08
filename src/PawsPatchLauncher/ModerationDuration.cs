using System.Globalization;

namespace PawsPatchLauncher;

public static class ModerationDuration
{
    public static bool TryDeadline(DateTimeOffset now,string days,string hours,string minutes,out DateTimeOffset deadline)
    {
        deadline=default;
        bool Number(string text,out int value)=>int.TryParse(text.Trim(),NumberStyles.None,CultureInfo.InvariantCulture,out value);
        if(!Number(days,out var d)||!Number(hours,out var h)||!Number(minutes,out var m)||h>23||m>59)return false;
        var total=(long)d*1440+h*60+m;
        if(total<1||total>(DateTimeOffset.MaxValue-now).TotalMinutes)return false;
        deadline=now.AddMinutes(total);
        return true;
    }
}
