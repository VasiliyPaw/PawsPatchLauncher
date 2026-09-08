using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;
public partial class MainWindow
{
    private static long? ResourceNumber(JsonElement data,string key)
        => data.ValueKind==JsonValueKind.Object && data.TryGetProperty(key,out var value) && value.ValueKind==JsonValueKind.Number && value.TryGetInt64(out var number) && number>=0 ? number : null;
    private string ResourceBytes(long value) => value>=1073741824 ? $"{value/1073741824d:0.##} GiB" : value>=1048576 ? $"{value/1048576d:0.##} MiB" : $"{value/1024d:0.##} KiB";
    private string ResourceBytes(JsonElement data,string key)=>ResourceNumber(data,key) is long value?ResourceBytes(value):"—";
    private void RenderAdminResources(JsonElement data)
    {
        if (_adminRows is null || _adminSummary is null) return;
        _adminRows.Children.Clear();
        var checkedAt=AccountService.ModerationDate(data,"checked_at");
        _adminSummary.Text=T("Замер: ","Measured: ")+(checkedAt is null?"—":ChatDate(checkedAt.Value))+"\n"+
            T("Обновление каждые 15 минут. Расход измерен; лимиты взяты из Free, тариф аккаунта не проверяется автоматически. Периоды писем — по UTC.",
            "Updated every 15 minutes. Usage is measured; quotas use Free-plan references, not an automatically verified subscription. Email periods use UTC.");
        var messages=ResourceNumber(data,"messages_count");
        AddResourceCard(T("База данных","Database"),ResourceNumber(data,"database_bytes"),ResourceNumber(data,"database_reference_limit"),true,
            T("Переписка: ","Messages: ")+(messages?.ToString("N0")??"—")+" · "+ResourceBytes(data,"messages_bytes")+
            T(" · карточки предложений: "," · offer metadata: ")+ResourceBytes(data,"offers_bytes"),MonitorRecent(checkedAt),checkedAt,referenceQuota:true);
        AddResourceCard(T("Файловое хранилище","File storage"),ResourceNumber(data,"storage_bytes"),ResourceNumber(data,"storage_reference_limit"),true,
            T("Сейвы: ","Saves: ")+ResourceBytes(data,"saves_bytes")+T(" · аватарки: "," · avatars: ")+ResourceBytes(data,"avatars_bytes"),MonitorRecent(checkedAt),checkedAt,referenceQuota:true);
        var metrics=data.TryGetProperty("provider_metrics",out var list)&&list.ValueKind==JsonValueKind.Array?list.EnumerateArray().ToArray():[];
        var monitor=MonitorObject(data,"monitor");var errors=MonitorObject(monitor,"errors");
        foreach(var (key,ru,en) in new[]{("emails_daily","Отправлено писем · день","Emails sent · day"),
            ("emails_monthly","Отправлено писем · месяц","Emails sent · month"),("functions_daily","Вызовы обработчиков · 24 часа","Function calls · 24 hours")})
        {
            var metric=metrics.FirstOrDefault(m=>m.TryGetProperty("metric",out var name)&&name.GetString()==key);
            var present=metric.ValueKind==JsonValueKind.Object;
            var stamp=present?AccountService.ModerationDate(metric,"checked_at"):null;
            var until=present?AccountService.ModerationDate(metric,"period_end"):null;
            var stale=!MonitorRecent(stamp)||until is not null&&until<=DateTimeOffset.UtcNow;
            var fault=MonitorString(errors,key);var partial=MonitorString(metric,"coverage")=="partial";
            var detail=!present?(fault is null?T("Ожидается первый замер провайдера.","Waiting for the first provider measurement."):MonitorError(fault)):
                (stale?T("Данные устарели. ","Stale data. "):"")+(fault is null?"":MonitorError(fault)+" ")+
                (partial?T("Частичный период: провайдер хранит не всю историю. Это не полный месячный расход. ","Partial period: provider retention does not cover the entire month. This is not the full monthly usage. "):"");
            long? quota=present?ResourceNumber(metric,"quota"):null;
            var badge=stale&&present?T("Устарело","Stale"):partial?T("Частично","Partial"):fault is not null&&present?T("Нет связи","Unavailable"):null;
            if(present){var from=AccountService.ModerationDate(metric,"period_start");var observed=AccountService.ModerationDate(metric,"observed_until");
                if(from is not null&&observed is not null)detail+=T("Период: ","Period: ")+from.Value.UtcDateTime.ToString("dd.MM.yyyy HH:mm:ss")+" — "+observed.Value.UtcDateTime.ToString("dd.MM.yyyy HH:mm:ss")+" UTC. ";
                if(key=="functions_daily")detail+=T("Запросы к обработчикам, включая ошибки. Это суточный замер, не месячный биллинг.","Function requests including errors. This is a 24-hour measurement, not monthly billing.");
                if(key.StartsWith("emails_")){quota=partial?null:key=="emails_daily"?100:3000;detail+=T("Учитываются отправленные, не входящие письма.","Counts sent emails, not incoming emails.");}
            }
            AddResourceCard(T(ru,en),present?ResourceNumber(metric,"used"):null,quota,false,detail,!stale&&!partial&&fault is null,stamp,badge,
                key.StartsWith("emails_")?ResendUsageUrl:null,referenceQuota:key.StartsWith("emails_"));
        }
        var retention=new StackPanel();
        retention.Children.Add(new TextBlock{Text=T("История диалогов","Conversation history"),FontSize=16,FontWeight=FontWeights.SemiBold});
        retention.Children.Add(new TextBlock{Text=T("10 000 сообщений → удаление 5 000 самых старых. Активные передачи защищены. Удалено: ",
            "10,000 messages → remove the oldest 5,000. Active transfers are protected. Removed: ")+(ResourceNumber(data,"removed_messages")?.ToString("N0")??"—"),
            TextWrapping=TextWrapping.Wrap,Foreground=SocialBrush("#A8BBD2"),Margin=new Thickness(0,6,0,0)});
        retention.Children.Add(new TextBlock{Text=T("Удалённое место PostgreSQL переиспользует: размер файла базы может уменьшиться не сразу.",
            "PostgreSQL reuses deleted space: the database file size may not shrink immediately."),TextWrapping=TextWrapping.Wrap,Foreground=SocialBrush("#A8BBD2"),FontSize=12,Margin=new Thickness(0,6,0,0)});
        _adminRows.Children.Add(AdminCard(retention));
        var traffic=new StackPanel();var trafficHeader=new DockPanel();
        var trafficBadge=StatusPill(T("В кабинете","In dashboard"),"#233248","#B7C8DA");DockPanel.SetDock(trafficBadge,Dock.Right);trafficHeader.Children.Add(trafficBadge);
        trafficHeader.Children.Add(new TextBlock{Text=T("Трафик Supabase","Supabase traffic"),FontSize=16,FontWeight=FontWeights.SemiBold});traffic.Children.Add(trafficHeader);
        traffic.Children.Add(new TextBlock{Text=T("Исходящий трафик и CDN-кэш: точный расход и лимиты доступны только в кабинете Supabase.",
            "Outgoing traffic and CDN cache: exact usage and quotas are available only in the Supabase dashboard."),TextWrapping=TextWrapping.Wrap,Foreground=SocialBrush("#A8BBD2"),FontSize=12,Margin=new Thickness(0,8,0,0)});
        traffic.Children.Add(MonitorDashboardButton(SupabaseUsageUrl));_adminRows.Children.Add(AdminCard(traffic));
    }
    private void AddResourceCard(string title,long? used,long? quota,bool bytes,string detail,bool fresh,DateTimeOffset? stamp,string? stateOverride=null,string? dashboardUrl=null,bool referenceQuota=false)
    {
        string Format(long n)=>bytes?ResourceBytes(n):n.ToString("N0");
        var body=new StackPanel();var header=new DockPanel();
        var ratio=used is not null&&quota>0?(double)used.Value/quota.Value:(double?)null;
        // Quota provenance is neutral; warning colours describe usage, not subscription verification.
        var color=used is null||!fresh?"#A8BBD2":ratio is null?"#D6E1EC":ratio>.75?"#FF9B92":ratio>.5?"#E8C36E":"#76DAB0";
        var state=stateOverride??(used is null?T("Нет данных","No data"):!fresh?T("Устарело","Stale"):referenceQuota?T("Лимит Free","Free-plan quota"):T("Замер API","API measurement"));
        var badge=StatusPill(state,"#233248",used is not null&&!fresh?"#E8C36E":"#B7C8DA");
        if(referenceQuota)badge.ToolTip=T("Расход измерен. Лимит взят из тарифа Free и не подтверждён для аккаунта автоматически.","Usage is measured. The quota is a Free-plan reference, not automatically verified for this account.");
        DockPanel.SetDock(badge,Dock.Right);header.Children.Add(badge);
        header.Children.Add(new TextBlock{Text=title,FontSize=16,FontWeight=FontWeights.SemiBold,VerticalAlignment=VerticalAlignment.Center});body.Children.Add(header);
        body.Children.Add(new TextBlock{Text=used is null?"—":Format(used.Value)+(quota>0?" / "+Format(quota.Value):"")+(ratio is null?"":$" · {ratio.Value:P1}"),FontSize=20,Margin=new Thickness(0,7,0,5),Foreground=SocialBrush(color)});
        if(ratio is not null)body.Children.Add(new ProgressBar{Minimum=0,Maximum=1,Value=Math.Clamp(ratio.Value,0,1),Height=5,Foreground=SocialBrush(color),Background=SocialBrush("#0C1C2E"),BorderThickness=new Thickness(0),Margin=new Thickness(0,1,0,7),
            ToolTip=T("Заполненность: до 50% включительно — зелёный, выше 50% до 75% — жёлтый, выше 75% — красный. Устаревший замер — серый.","Usage: up to 50% green, above 50% through 75% yellow, above 75% red. Stale measurements are grey.")});
        body.Children.Add(new TextBlock{Text=detail+(stamp is null?"":"\n"+T("Обновлено: ","Updated: ")+ChatDate(stamp.Value)),TextWrapping=TextWrapping.Wrap,Foreground=SocialBrush("#A8BBD2"),FontSize=12});
        if(dashboardUrl is not null)body.Children.Add(MonitorDashboardButton(dashboardUrl));
        _adminRows?.Children.Add(AdminCard(body));
    }
}
