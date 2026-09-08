using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;
public partial class MainWindow
{
    private const string SupabaseUsageUrl="https://supabase.com/dashboard/org/djdymwmalenggwwgiein/usage?projectRef=trdzsdclscuwwmxnepyt";
    private const string ResendUsageUrl="https://resend.com/settings/usage";
    private static JsonElement MonitorObject(JsonElement data,string key)
        =>data.ValueKind==JsonValueKind.Object&&data.TryGetProperty(key,out var value)&&value.ValueKind==JsonValueKind.Object?value:default;
    private static string? MonitorString(JsonElement data,string key)
        =>data.ValueKind==JsonValueKind.Object&&data.TryGetProperty(key,out var value)&&value.ValueKind==JsonValueKind.String?value.GetString():null;
    private static bool? MonitorBool(JsonElement data,string key)
        =>data.ValueKind==JsonValueKind.Object&&data.TryGetProperty(key,out var value)&&value.ValueKind is JsonValueKind.True or JsonValueKind.False?value.GetBoolean():null;
    private static bool MonitorRecent(DateTimeOffset? stamp)=>stamp is not null&&stamp>=DateTimeOffset.UtcNow.AddMinutes(-30)&&stamp<=DateTimeOffset.UtcNow.AddMinutes(2);
    private string MonitorError(string? error)=>error switch {
        "access_denied"=>T("Провайдер отклонил серверный ключ.","Provider rejected the server key."),
        "rate_limited"=>T("Провайдер ограничил частоту запросов. Повтор — в следующем цикле.","Provider rate limit. Retrying in the next cycle."),
        "unreachable"=>T("Провайдер не ответил. Повтор — в следующем цикле.","Provider did not respond. Retrying in the next cycle."),
        "domain_missing"=>T("Почтовый домен не найден.","Email domain not found."),
        _=>T("Нет корректного ответа провайдера.","No valid provider response.")};
    private Button MonitorDashboardButton(string url)
    {
        var button=new Button{Style=(Style)FindResource("GhostButton"),Content=T("Открыть кабинет ↗","Open dashboard ↗"),HorizontalAlignment=HorizontalAlignment.Left,Margin=new Thickness(0,9,0,0),Padding=new Thickness(12,5,12,5),FontSize=12};
        button.Click+=async(_,_)=>{
            // Fixed, known provider URLs only. Never open a URL supplied in a remote snapshot.
            if(url!=SupabaseUsageUrl&&url!=ResendUsageUrl)return;
            button.IsEnabled=false;
            try{await _openHelpLink(url);}
            catch{ShowToast(()=>T("Не удалось открыть браузер.","Could not open the browser."),true);}
            finally{button.IsEnabled=true;}
        };
        return button;
    }
    private void RenderMonitorStatus(JsonElement monitor)
    {
        var stamp=AccountService.ModerationDate(monitor,"checked_at");var recent=MonitorRecent(stamp);
        var suffix=stamp is null?T("\nПервый замер ещё не получен.","\nNo measurement received yet."):"\n"+T("Замер: ","Measured: ")+ChatDate(stamp.Value);
        void Row(string title,bool? good,string detail,bool warning=false){
            var state=!recent?T("Данные устарели","Stale status"):good is null?T("Нет данных","No data"):good==false?T("Ошибка","Error"):warning?T("Внимание","Attention"):T("Работает","Operational");
            AddAdminStatus(title,state,detail+suffix,!recent||good is null||warning?"warning":good==true?"ok":"error");
        }
        var services=monitor.TryGetProperty("services",out var items)&&items.ValueKind==JsonValueKind.Array?items.EnumerateArray().ToArray():[];
        foreach(var (name,ru,en) in new[]{("auth","Авторизация Supabase","Supabase Auth"),("db","Состояние базы Supabase","Supabase database health"),("rest","API данных","Data API"),("storage","API хранилища","Storage API")}){
            var service=services.FirstOrDefault(s=>MonitorString(s,"name")==name);var good=MonitorBool(service,"healthy");
            Row(T(ru,en),good,good is null?MonitorError(MonitorString(service,"error")):T("Проверка состояния сервиса через Supabase.","Service health reported by Supabase."));
        }
        var email=MonitorObject(monitor,"email");var daily=MonitorObject(email,"daily");
        var emailReady=MonitorBool(email,"api_available")==true&&MonitorBool(email,"domain_verified")==true;
        var sent=ResourceNumber(daily,"sent");var delivered=ResourceNumber(daily,"delivered");var failed=ResourceNumber(daily,"failed");var bounced=ResourceNumber(daily,"bounced");
        var emailDetail=emailReady?T("Домен pawspatch.xyz подтверждён. За день: отправлено ","Domain pawspatch.xyz is verified. Today: sent ")+(sent?.ToString()??"—")+
            T(", доставлено ",", delivered ")+(delivered?.ToString()??"—")+T(", ошибок ",", failed ")+(failed?.ToString()??"—")+T(", возвратов ",", bounced ")+(bounced?.ToString()??"—")+".":MonitorBool(email,"api_available")==true?T("Домен ещё не готов к отправке писем.","The domain is not ready to send emails."):MonitorError(MonitorString(email,"error"));
        Row(T("Отправка писем · Resend","Email sending · Resend"),emailReady,emailDetail+T("\nСтатистика доставки прошлых писем; тестовые письма не отправляются.","\nDelivery statistics for previous emails; no test emails are sent."),sent is null||failed>0||bounced>0);
        var storage=MonitorObject(monitor,"storage");var storageReady=MonitorBool(storage,"api_available")==true&&MonitorBool(storage,"private_bucket")==true;
        Row(T("Хранилище сейвов","Save storage"),storageReady,storageReady?T("Приватное хранилище доступно. Максимальный файл: ","Private bucket available. Maximum file: ")+ResourceBytes(storage,"file_limit")+
            T(". Проверено чтение параметров, не тестовая передача сейва.",". Bucket metadata checked; no test save was transferred."):MonitorError(MonitorString(storage,"error")));
        var functions=MonitorObject(monitor,"functions");var deployed=ResourceNumber(functions,"deployed");var active=ResourceNumber(functions,"active");var errors=ResourceNumber(functions,"server_errors");
        Row(T("Серверные обработчики","Server functions"),deployed is null?null:deployed==active,
            T("Активны: ","Active: ")+(active?.ToString()??"—")+" / "+(deployed?.ToString()??"—")+T(". Ошибки сервера за 24 часа: ",". Server errors in 24 hours: ")+(errors?.ToString()??"—")+".",errors is null||errors>0);
        var expiry=AccountService.ModerationDate(monitor,"token_expires_at");var expired=expiry<=DateTimeOffset.UtcNow;var soon=expiry<=DateTimeOffset.UtcNow.AddDays(7);
        AddAdminStatus(T("Обновление мониторинга","Monitoring refresh"),expired?T("Ключ истёк","Key expired"):!recent?T("Нет свежих данных","No fresh data"):soon?T("Обновите ключ","Renew key"):T("Каждые 15 минут","Every 15 minutes"),
            T("Ключи используются только на сервере.","Keys are used only on the server.")+(expiry is null?"":"\n"+T("Заменить ключ Supabase до: ","Replace Supabase key before: ")+ChatDate(expiry.Value))+suffix,
            expired?"error":!recent||soon||expiry is null?"warning":"ok");
    }
}
