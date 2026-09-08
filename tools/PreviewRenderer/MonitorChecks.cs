using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class MonitorChecks
{
    private const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
    private static object? Call(MainWindow w,string method,params object[] args)=>typeof(MainWindow).GetMethod(method,Flags)!.Invoke(w,args);
    private static T Field<T>(MainWindow w,string name)=>(T)typeof(MainWindow).GetField(name,Flags)!.GetValue(w)!;
    private static IEnumerable<T> Desc<T>(DependencyObject d)where T:DependencyObject{if(d is T t)yield return t;for(var i=0;i<VisualTreeHelper.GetChildrenCount(d);i++)foreach(var c in Desc<T>(VisualTreeHelper.GetChild(d,i)))yield return c;}
    private static JsonDocument Fixture(bool stale=false,bool partial=false,bool failed=false,bool expired=false)
    {
        var now=DateTimeOffset.UtcNow;var stamp=stale?now.AddHours(-2):now;
        return JsonDocument.Parse(JsonSerializer.Serialize(new{checked_at=now,cleanup_at=now.AddMinutes(-2),cleanup_ok=true,
            database_bytes=13000000,messages_count=67,messages_bytes=81920,offers_bytes=32768,storage_bytes=0,saves_bytes=0,avatars_bytes=0,removed_messages=0,
            database_reference_limit=524288000,storage_reference_limit=1073741824,
            provider_metrics=new[]{"emails_daily","emails_monthly","functions_daily"}.Select(metric=>new{metric,used=metric=="functions_daily"?145:2,checked_at=stamp,
                period_start=now.AddHours(-8),observed_until=now,coverage=partial?"partial":"complete"}),
            monitor=new{checked_at=stamp,token_expires_at=expired?now.AddDays(-1):now.AddDays(30),
                errors=new{egress="billing_api_unavailable",cached_egress="billing_api_unavailable",emails_daily=failed?"access_denied":(string?)null},
                services=new[]{"auth","db","rest","storage"}.Select(name=>new{name,healthy=!failed}),
                email=new{api_available=!failed,domain_verified=!failed,daily=new{sent=2,delivered=2,failed=0,bounced=0}},
                storage=new{api_available=true,private_bucket=true,file_limit=20971520},functions=new{deployed=5,active=5,server_errors=failed?4:0}}}));
    }
    internal static void Populate(MainWindow w,string mode)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Fixture only");
        if(mode=="resources")HistoryResourceChecks.PopulateResources(w);else AdminChecks.Populate(w,"status");
        using var data=Fixture();Call(w,mode=="resources"?"RenderAdminResources":"RenderAdminStatus",data.RootElement);
    }
    internal static void Run(MainWindow w,string language,Action<bool,string> check)
    {
        string S(string ru,string en)=>language=="ru"?ru:en;
        StackPanel Rows()=>Field<StackPanel>(w,"_adminRows");
        string Text()=>string.Join('\n',Desc<TextBlock>(Rows()).Select(t=>t.Text));
        using(var data=Fixture()){Call(w,"RenderAdminResources",data.RootElement);w.UpdateLayout();}
        check(Rows().Children.Count==7,"connected resource card count");
        check(Desc<TextBlock>(Rows()).Count(t=>t.Text==S("В кабинете","In dashboard"))==1,"traffic not combined");
        var titles=Rows().Children.Cast<DependencyObject>().Select(card=>Desc<TextBlock>(card).First(t=>t.FontSize==16).Text).ToArray();
        check(titles.SequenceEqual(new[]{S("База данных","Database"),S("Файловое хранилище","File storage"),S("Отправлено писем · день","Emails sent · day"),S("Отправлено писем · месяц","Emails sent · month"),S("Вызовы обработчиков · 24 часа","Function calls · 24 hours"),S("История диалогов","Conversation history"),S("Трафик Supabase","Supabase traffic")}),"resource order");
        check(Desc<TextBlock>(Rows()).Count(t=>t.Text==S("Нет данных","No data"))==0,"connected measurements absent");
        check(Desc<ProgressBar>(Rows()).Count()==4,"only database, storage and email reference progress");
        check(Text().Contains(S("24 часа","24 hours"))&&Text().Contains(S("не месячный биллинг","not monthly billing")),"function window mislabeled");
        check(Desc<Button>(Rows()).Count()==3,"dashboard link count");
        check(Desc<ProgressBar>(Rows()).All(p=>p.Foreground.ToString()=="#FF76DAB0"),"fresh low usage should be uniformly green");
        check(Desc<TextBlock>(Rows()).Count(t=>t.Text==S("Лимит Free","Free-plan quota")&&t.Foreground.ToString()=="#FFB7C8DA")==4,"reference quota badges inconsistent");
        foreach(var (used,color) in new[]{(0,"#FF76DAB0"),(50,"#FF76DAB0"),(51,"#FFE8C36E"),(75,"#FFE8C36E"),(76,"#FFFF9B92"),(100,"#FFFF9B92"),(101,"#FFFF9B92")}){
            using var usage=JsonDocument.Parse(JsonSerializer.Serialize(new{checked_at=DateTimeOffset.UtcNow,provider_metrics=new[]{new{metric="emails_daily",used,checked_at=DateTimeOffset.UtcNow}}}));
            Call(w,"RenderAdminResources",usage.RootElement);w.UpdateLayout();
            var progress=Desc<ProgressBar>(Rows()).Single();check(progress.Foreground.ToString()==color&&progress.Value<=1,"usage threshold / overflow");
        }
        using(var data=Fixture(stale:true)){Call(w,"RenderAdminResources",data.RootElement);w.UpdateLayout();}
        check(Desc<ProgressBar>(Rows().Children[2]).Single().Foreground.ToString()=="#FFA8BBD2","stale usage looks current");
        check(Desc<Button>(Rows()).All(b=>ReferenceEquals(b.Style,w.FindResource("GhostButton"))),"dashboard button lost dark theme");
        using(var data=Fixture(partial:true)){Call(w,"RenderAdminResources",data.RootElement);w.UpdateLayout();}
        check(Text().Contains(S("Частичный период","Partial period")),"retention-clamped stats hidden");
        check(Desc<ProgressBar>(Rows()).Count()==2,"partial month presented as quota percentage");
        using(var data=Fixture(failed:true)){Call(w,"RenderAdminResources",data.RootElement);w.UpdateLayout();}
        check(Text().Contains(S("Провайдер отклонил","Provider rejected"))&&Text().Contains(S("Нет связи","Unavailable")),"old values shown verified after rejection");
        using(var data=Fixture()){Call(w,"RenderAdminStatus",data.RootElement);w.UpdateLayout();}
        check(Rows().Children.Count==11,"connected service count");
        check(!Text().Contains(S("Не проверено","Not checked")),"connected services still placeholders");
        check(Text().Contains(S("доставлено 2","delivered 2")),"delivery totals missing");
        check(Text().Contains(S("не тестовая передача","no test save")),"metadata probe presented as actual save transfer");
        using(var data=Fixture(stale:true)){Call(w,"RenderAdminStatus",data.RootElement);w.UpdateLayout();}
        check(Desc<TextBlock>(Rows()).Count(t=>t.Text==S("Данные устарели","Stale status"))==7,"stale providers shown green");
        using(var data=Fixture(failed:true,expired:true)){Call(w,"RenderAdminStatus",data.RootElement);w.UpdateLayout();}
        check(Text().Contains(S("Ключ истёк","Key expired")),"token expiry absent");
        check(Desc<TextBlock>(Rows()).Count(t=>t.Text==S("Ошибка","Error"))>=5,"unhealthy provider not red");
        Populate(w,"resources");
    }
}
