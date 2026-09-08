using System.Globalization;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private string _adminOwner="",_adminSection="status",_adminLanguage="",_adminQuery="";
    private int _adminPage,_adminRequest;
    private bool _adminBusy;
    private AdminPage? _adminData;
    private StackPanel? _adminRows;
    private TextBox? _adminSearch;
    private TextBlock? _adminSummary;
    private Button? _adminPrevious,_adminNext;
    private readonly DispatcherTimer _adminSearchTimer=new(){Interval=TimeSpan.FromMilliseconds(280)};
    private bool _adminInitialized;
    private SocialPlayer? _adminViewedPlayer;
    // Smoke-only transport seam: exercises confirmations without changing real accounts.
    private Func<string,Guid,string,DateTimeOffset?,int?,Task>? _adminActionOverride = null;

    private async void AdminNav_Click(object sender,RoutedEventArgs e)
    {
        if(_account.AdminLevel<1||ConfirmationActive)return;
        SetActivePage("admin");BuildAdminLayout();await LoadAdminAsync();
    }
    private void BuildAdminLayout()
    {
        if(!_adminInitialized)
        {
            _adminInitialized=true;
            _adminSearchTimer.Tick+=async(_,_)=>{_adminSearchTimer.Stop();await LoadAdminAsync();};
            Closed+=(_,_)=>{_adminSearchTimer.Stop();_adminRequest++;};
        }
        _adminLanguage=_text.Language;
        AdminHeaderPanel.Children.Clear();
        AdminContentPanel.Children.Clear();
        AdminContentScroll.ScrollToTop();
        AdminHeaderPanel.Children.Add(new TextBlock{Text=T("Администрирование","Administration"),FontSize=24,FontWeight=FontWeights.Bold,Margin=new Thickness(0,0,0,14)});
        var tabs=new WrapPanel{Margin=new Thickness(0,0,0,10)};
        foreach(var (key,ru,en) in new[]{("status","Статус","Status"),("resources","Ресурсы","Resources"),("users","Пользователи","Users"),("bans","Блокировки","Bans"),("deleted","Удалённые","Deleted")})
        {
            var tab=SocialButton(T(ru,en),async()=>{if(_adminSection==key||_adminBusy)return;_adminRequest++;_adminSection=key;_adminPage=0;_adminData=null;BuildAdminLayout();RevealAdminRows();await LoadAdminAsync();if(_adminSection==key)RevealAdminRows();});
            tab.Tag=key;SetNavState(tab,_adminSection==key);tabs.Children.Add(tab);
        }
        var tabBar=new DockPanel();tabBar.Children.Add(tabs);AdminHeaderPanel.Children.Add(tabBar);
        var searchRow=new DockPanel{Margin=new Thickness(0,0,0,12)};
        var refresh=SocialButton(T("Обновить","Refresh"),LoadAdminAsync);refresh.Height=36;refresh.Margin=new Thickness(8,0,0,0);DockPanel.SetDock(refresh,Dock.Right);
        if(_adminSection is "status" or "resources"){tabBar.Children.Insert(0,refresh);refresh.VerticalAlignment=VerticalAlignment.Top;searchRow.Visibility=Visibility.Collapsed;}
        else searchRow.Children.Add(refresh);
        _adminSearch=new TextBox{Style=(Style)FindResource("ConfigurationInput"),Text=_adminQuery,MaxLength=64,Height=36,VerticalContentAlignment=VerticalAlignment.Center,
            ToolTip=_adminSection=="bans"?T("Поиск по почте","Search by email"):T("Имя или username","Display name or username"),Visibility=_adminSection is "status" or "resources"?Visibility.Collapsed:Visibility.Visible};
        System.Windows.Automation.AutomationProperties.SetName(_adminSearch,_adminSearch.ToolTip.ToString());
        _adminSearch.TextChanged+=(_,_)=>{_adminQuery=_adminSearch.Text;_adminPage=0;_adminRequest++;_adminData=null;_adminSearchTimer.Stop();_adminSearchTimer.Start();};
        searchRow.Children.Add(_adminSearch);AdminHeaderPanel.Children.Add(searchRow);
        _adminSummary=new TextBlock{Text=T("Загрузка…","Loading…"),Foreground=SocialBrush("#A8BBD2"),TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,0,0,12)};
        AdminHeaderPanel.Children.Add(_adminSummary);_adminRows=new StackPanel();AdminContentPanel.Children.Add(_adminRows);
        var pages=new WrapPanel{Margin=new Thickness(0,6,0,0)};
        _adminPrevious=SocialButton(T("Назад","Previous"),async()=>{if(_adminPage>0){_adminPage--;await LoadAdminAsync();}});
        _adminNext=SocialButton(T("Далее","Next"),async()=>{_adminPage++;await LoadAdminAsync();});
        pages.Children.Add(_adminPrevious);pages.Children.Add(_adminNext);pages.Visibility=_adminSection is "status" or "resources"?Visibility.Collapsed:Visibility.Visible;
        AdminContentPanel.Children.Add(pages);RenderAdminRows();
    }
    private async Task LoadAdminAsync()
    {
        if(_account.AdminLevel<1||_activePage!="admin"||ActivityStore.IsSmokeTest)return;
        var request=++_adminRequest;var owner=_account.UserId;var section=_adminSection;var page=_adminPage;var query=_adminQuery;
        if(_adminSummary is not null)_adminSummary.Text=T("Обновляем…","Refreshing…");
        try
        {
            if(section=="status")
            {
                var state=await _account.GetAdminStatusAsync(_accountLifetime.Token);
                if(request!=_adminRequest||owner!=_account.UserId||_account.AdminLevel<1)return;
                RenderAdminStatus(state);
            }
            else if(section=="resources")
            {
                var state=await _account.GetAdminResourcesAsync(_accountLifetime.Token);
                if(request!=_adminRequest||owner!=_account.UserId||_account.AdminLevel<1)return;
                RenderAdminResources(state);
            }
            else
            {
                var data=await _account.GetAdminPageAsync(section,query,page,_accountLifetime.Token);
                if(request!=_adminRequest||owner!=_account.UserId||_account.AdminLevel<1)return;
                _adminData=data;RenderAdminRows();
            }
        }
        catch(OperationCanceledException){}
        catch(AccountException error)
        {
            if(owner!=_account.UserId||request!=_adminRequest)return;
            if(error.Code is "admin_required" or "higher_role_required") {_adminData=null;_adminRows?.Children.Clear();}
            if(_adminSummary is not null)_adminSummary.Text=AccountMessage(error.Code);
            if(section is "status" or "resources")RenderAdminStatusFailure();
        }
        catch {if(request==_adminRequest&&_adminSummary is not null){_adminSummary.Text=T("Не удалось загрузить данные.","Could not load data.");if(section is "status" or "resources")RenderAdminStatusFailure();}}
    }
    private void RenderAdminStatusFailure()
    {
        _adminRows?.Children.Clear();
        AddAdminStatus(T("Соединение с сервером","Server connection"),T("Ошибка проверки","Check failed"),T("Не удалось получить актуальные статусы. Попробуйте обновить ещё раз.","Could not retrieve current statuses. Try refreshing again."),"error");
    }
    private Border AdminCard(UIElement body)=>new(){Child=body,Background=SocialBrush("#13283F"),BorderBrush=SocialBrush("#34516D"),BorderThickness=new Thickness(1),CornerRadius=new CornerRadius(10),Padding=new Thickness(14),Margin=new Thickness(0,0,0,10)};
    private void RevealAdminRows()
    {
        if(_adminRows is null)return;
        var transform=new TranslateTransform();_adminRows.RenderTransform=transform;
        Motion.RevealFromBottom(_adminRows,transform);
    }
    private Button AdminButton(string text,Func<Task> action,bool danger=false)
    {
        var b=SocialButton(text,action);b.Padding=new Thickness(10,7,10,7);b.FontSize=12;
        if(danger){b.Content=new TextBlock{Text=text,Foreground=SocialBrush("#FFB1A8")};b.Foreground=SocialBrush("#FFB1A8");b.BorderBrush=SocialBrush("#80515A");}
        return b;
    }
    private void RenderAdminRows()
    {
        if(_adminRows is null||_adminSummary is null)return;
        _adminRows.Children.Clear();
        if(_adminPrevious is not null)_adminPrevious.IsEnabled=_adminPage>0;
        if(_adminNext is not null)_adminNext.IsEnabled=_adminData?.More==true;
        if(_adminData is null)return;
        var data=_adminData;
        _adminSummary.Text=T("Страница ","Page ")+(_adminPage+1)+T(" · новые сверху · проверено "," · newest first · checked ")+ChatDate(data.ServerTime);
        foreach(var user in data.Users)
        {
            var body=new StackPanel();
            var name=new WrapPanel();name.Children.Add(new TextBlock{Text=user.DisplayName,FontSize=18,FontWeight=FontWeights.SemiBold,VerticalAlignment=VerticalAlignment.Center,Margin=new Thickness(0,0,8,0)});
            name.Children.Add(new TextBlock{Text="@"+user.Nickname,Foreground=SocialBrush("#A8BBD2"),VerticalAlignment=VerticalAlignment.Center});
            if(user.AdminLevel>0)name.Children.Add(AdministratorBadge(user.AdminLevel));body.Children.Add(name);
            var time=new WrapPanel{Margin=new Thickness(0,7,0,0)};
            time.Children.Add(new TextBlock{Text=T("Регистрация: ","Registered: ")+ChatDate(user.CreatedAt),Foreground=SocialBrush("#A8BBD2"),FontSize=12,VerticalAlignment=VerticalAlignment.Center});
            if(user.IsNew)time.Children.Add(StatusPill(T("Новый пользователь","New user"),"#193F34","#83E5B3"));body.Children.Add(time);
            if(user.BannedAt is not null&&(user.BanUntil is null||user.BanUntil>data.ServerTime))body.Children.Add(new TextBlock{Text=BanDescription(user.BannedAt,user.BanUntil,user.BanReason),Foreground=SocialBrush("#FFB1A8"),TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,0)});
            if(user.DeletedAt is DateTimeOffset deleted)body.Children.Add(new TextBlock{Text=T("Удалён: ","Deleted: ")+ChatDate(deleted)+"\n"+T("Восстановление до: ","Recoverable until: ")+ChatDate(deleted.AddDays(7)),Foreground=SocialBrush("#FFB1A8"),Margin=new Thickness(0,8,0,0)});
            var buttons=new WrapPanel{Margin=new Thickness(0,8,0,0)};
            var own=user.Id.ToString()==_account.UserId;
            var banned=user.BannedAt is not null&&(user.BanUntil is null||user.BanUntil>data.ServerTime);
            if(user.DeletedAt is null)
            {
                buttons.Children.Add(AdminButton(T("Профиль","Profile"),()=>OpenAdminProfileAsync(user.Id)));
                var chat=AdminButton(T("Написать","Message"),()=>OpenAdminChatAsync(user.Id));chat.IsEnabled=!own&&!(user.BannedAt is not null&&(user.BanUntil is null||user.BanUntil>data.ServerTime));buttons.Children.Add(chat);
                var add=AdminButton(T("Добавить в друзья","Add friend"),()=>AdminAddFriendAsync(user));add.IsEnabled=chat.IsEnabled;buttons.Children.Add(add);
                var ban=AdminButton(T("Заблокировать почту","Ban email"),()=>ModerateAsync(user,"ban"),true);
                var del=AdminButton(T("Удалить аккаунт","Delete account"),()=>ModerateAsync(user,"delete"),true);
                del.IsEnabled=!own&&!user.Protected&&(_account.AdminLevel==2||user.AdminLevel==0);
                ban.IsEnabled=del.IsEnabled&&!banned;buttons.Children.Add(ban);buttons.Children.Add(del);
                if(_account.AdminLevel==2)
                {
                    var role=AdminButton(T("Права…","Roles…"),()=>ModerateAsync(user,"role"));role.IsEnabled=!own&&!user.Protected&&!banned;buttons.Children.Add(role);
                }
            }
            else
            {
                var restore=AdminButton(T("Восстановить аккаунт","Restore account"),()=>ModerateAsync(user,"restore"));
                restore.IsEnabled=!user.Purging&&user.DeletedAt.Value.AddDays(7)>data.ServerTime&&(_account.AdminLevel==2||user.AdminLevel==0);buttons.Children.Add(restore);
                var ban=AdminButton(T("Заблокировать почту","Ban email"),()=>ModerateAsync(user,"ban"),true);ban.IsEnabled=!banned&&!user.Protected&&!user.Purging&&(_account.AdminLevel==2||user.AdminLevel==0);buttons.Children.Add(ban);
            }
            body.Children.Add(buttons);_adminRows.Children.Add(AdminCard(body));
        }
        foreach(var ban in data.Bans)
        {
            var body=new StackPanel();body.Children.Add(new TextBlock{Text=ban.Email,FontSize=18,FontWeight=FontWeights.SemiBold});
            body.Children.Add(new TextBlock{Text=BanDescription(ban.CreatedAt,ban.Until,ban.Reason),Foreground=SocialBrush("#FFB1A8"),TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,6)});
            body.Children.Add(AdminButton(T("Разблокировать","Unban"),async()=>
            {
                var owner=_account.UserId;
                if(await ConfirmActionAsync(T("Снять блокировку?","Remove ban?"),T("Адрес снова можно будет использовать для аккаунта.","This email will be available for accounts again."),T("ПОЧТА","EMAIL"),ban.Email,T("Разблокировать","Unban"))&&owner==_account.UserId)
                    await RunAdminMutationAsync(()=>_account.AdminActionAsync("unban",ban.Id,ct:_accountLifetime.Token));
            }));_adminRows.Children.Add(AdminCard(body));
        }
        if(data.Users.Count+data.Bans.Count==0)_adminRows.Children.Add(new TextBlock{Text=T("Ничего не найдено","No results"),Foreground=SocialBrush("#A8BBD2"),Margin=new Thickness(0,14,0,0)});
    }
    private void RenderAdminStatus(JsonElement state)
    {
        if(_adminRows is null||_adminSummary is null)return;
        _adminRows.Children.Clear();
        var checkedAt=AccountService.ModerationDate(state,"checked_at")??DateTimeOffset.UtcNow;
        _adminSummary.Text=T("Проверено: ","Checked: ")+ChatDate(checkedAt);
        AddAdminStatus(T("База данных и права доступа","Database and authorization"),T("Работает","Operational"),T("Защищённый запрос выполнен.","Authenticated query completed."),"ok");
        AddAdminStatus(T("Сессия аккаунта","Account session"),T("Активна","Active"),T("Сервер подтвердил этот лаунчер.","This launcher was verified by the server."),"ok");
        var monitor=MonitorObject(state,"monitor");
        if(monitor.ValueKind==System.Text.Json.JsonValueKind.Object)RenderMonitorStatus(monitor);
        else {
        AddAdminStatus(T("Письма","Email"),T("Не проверено","Not checked"),T("Нет данных о доставке. Тестовые письма автоматически не отправляются.","Delivery data unavailable. No automatic test emails are sent."),"warning");
        AddAdminStatus(T("Хранилище сейвов","Save storage"),T("Не проверено","Not checked"),T("Загрузка проверяется при передаче сейва. Отдельный тест не запускался.","Uploads are checked during save transfers. No separate test has been run."),"warning");
        }
        var stamp=AccountService.ModerationDate(state,"cleanup_at");
        var ok=AccountService.ModerationBool(state,"cleanup_ok");
        var recent=stamp is not null&&checkedAt-stamp.Value<TimeSpan.FromMinutes(15);
        AddAdminStatus(T("Очистка удалённых аккаунтов","Deleted account cleanup"),
            stamp is null?T("Ожидание","Pending"):!ok?T("Ошибка","Error"):!recent?T("Данные устарели","Stale status"):T("Работает","Operational"),
            T("Удаляет аккаунты после 7 дней, отведённых на восстановление.","Removes accounts after the 7-day recovery period.")+
            (stamp is null?"": "\n"+T("Последняя проверка: ","Last check: ")+ChatDate(stamp.Value))+
            (stamp is not null&&!ok?"\n"+T("Повторная попытка будет автоматической.","The next attempt is automatic."):""),
            stamp is null||ok&&!recent?"warning":ok?"ok":"error");
    }
    private void AddAdminStatus(string title,string status,string detail,string tone)
    {
        var colors=tone switch{"ok"=>("#193F34","#83E5B3"),"error"=>("#4A2831","#FFB1A8"),_=>("#483B20","#F0D18A")};
        var body=new StackPanel();var heading=new DockPanel();
        var pill=StatusPill(status,colors.Item1,colors.Item2);DockPanel.SetDock(pill,Dock.Right);heading.Children.Add(pill);
        heading.Children.Add(new TextBlock{Text=title,FontSize=16,FontWeight=FontWeights.SemiBold,TextWrapping=TextWrapping.Wrap,VerticalAlignment=VerticalAlignment.Center});
        body.Children.Add(heading);body.Children.Add(new TextBlock{Text=detail,TextWrapping=TextWrapping.Wrap,Foreground=SocialBrush("#B7C8DA"),Margin=new Thickness(0,8,0,0)});
        _adminRows?.Children.Add(AdminCard(body));
    }
    private async Task ModerateAsync(AdminPlayer user,string action)
    {
        if(_adminBusy||_account.AdminLevel<1||ConfirmationActive)return;
        if(action=="ban"&&user.BannedAt is not null&&(user.BanUntil is null||user.BanUntil>DateTimeOffset.UtcNow))return;
        var owner=_account.UserId;
        var title=action switch{"ban"=>T("Заблокировать почту?","Ban email?"),"delete"=>T("Удалить аккаунт?","Delete account?"),"restore"=>T("Восстановить аккаунт?","Restore account?"),_=>T("Права администратора","Administrator privileges")};
        var details=action switch{"ban"=>T("Аккаунт останется. Общение и изменение профиля будут недоступны; игра и обновления продолжат работать.","The account remains. Social features and profile editing will be disabled; local game and updates remain available."),"delete"=>T("Профиль скроется, в чатах останется «Удалённый аккаунт». Восстановление доступно 7 дней. После этого удаление необратимо.","The profile is hidden and chats show a deleted account. Recoverable for 7 days, then permanently deleted."),"restore"=>T("Вернутся профиль и доступ к аккаунту. Если почта заблокирована, блокировка сохранится.","Restores the profile and account. Any email ban remains in force."),_=>T("Обычный администратор модерирует пользователей. Главный также назначает и снимает администраторов.","Administrators moderate users. Senior administrators also grant and revoke roles.")};
        var pending=ConfirmActionAsync(title,details,T("ПОЛЬЗОВАТЕЛЬ","USER"),user.DisplayName+" · @"+user.Nickname,action=="role"?T("Сохранить права","Save privileges"):title.TrimEnd('?'));
        if(!ConfirmationActive)return;
        var reason=new TextBox{Style=(Style)FindResource("ConfigurationInput"),MaxLength=500,Height=60,TextWrapping=TextWrapping.Wrap,AcceptsReturn=false};
        var permanent=new CheckBox{Content=T("Постоянная блокировка","Permanent ban"),IsChecked=false,Margin=new Thickness(0,10,0,10)};
        var duration=new Grid{Margin=new Thickness(0,0,0,8)};
        var durationFields=new List<TextBox>();
        foreach(var (ru,en,value) in new[]{("Дни","Days","1"),("Часы","Hours","0"),("Минуты","Minutes","0")})
        {
            var index=durationFields.Count;duration.ColumnDefinitions.Add(new ColumnDefinition());
            var cell=new StackPanel{Margin=new Thickness(index==0?0:10,0,0,0)};
            cell.Children.Add(new TextBlock{Text=T(ru,en),Foreground=SocialBrush("#B7C8DA"),Margin=new Thickness(0,0,0,5)});
            var input=new TextBox{Style=(Style)FindResource("ConfigurationInput"),Text=value,MaxLength=7,Height=38,VerticalContentAlignment=VerticalAlignment.Center,Tag=en};
            System.Windows.Automation.AutomationProperties.SetName(input,T(ru,en));
            durationFields.Add(input);cell.Children.Add(input);Grid.SetColumn(cell,index);duration.Children.Add(cell);
        }
        var level=user.AdminLevel;
        DateTimeOffset? end=null;
        if(action is "ban" or "role")
        {
            ConfirmationChangesPanel.Visibility=Visibility.Visible;
            if(action=="ban")
            {
                ConfirmationChangesPanel.Children.Add(new TextBlock{Text=T("Причина блокировки","Ban reason")});ConfirmationChangesPanel.Children.Add(reason);
                ConfirmationChangesPanel.Children.Add(permanent);
                ConfirmationChangesPanel.Children.Add(duration);
                var hint=new TextBlock{FontSize=12,Foreground=SocialBrush("#B7C8DA"),TextWrapping=TextWrapping.Wrap};ConfirmationChangesPanel.Children.Add(hint);
                void Validate()
                {
                    var valid=ModerationDuration.TryDeadline(DateTimeOffset.UtcNow,durationFields[0].Text,durationFields[1].Text,durationFields[2].Text,out var parsed);
                    end=valid?parsed:null;duration.IsEnabled=permanent.IsChecked!=true;
                    hint.Text=permanent.IsChecked==true?T("Без ограничения срока.","No expiry."):!valid?T("Укажите срок от 1 минуты. Часы: 0–23, минуты: 0–59.","Enter at least 1 minute. Hours: 0–23, minutes: 0–59."):
                        T("Блокировка до: ","Banned until: ")+ChatDate(parsed);
                    ConfirmationDeleteButton.IsEnabled=reason.Text.Trim().Length>0&&(permanent.IsChecked==true||valid);
                }
                reason.TextChanged+=(_,_)=>Validate();foreach(var input in durationFields)input.TextChanged+=(_,_)=>Validate();permanent.Checked+=(_,_)=>Validate();permanent.Unchecked+=(_,_)=>Validate();Validate();
            }
            else
            {
                var choices=new StackPanel{Margin=new Thickness(0,10,0,2)};
                var labels=new[]{T("Пользователь · без прав","User · no privileges"),T("Администратор","Administrator"),T("Главный администратор","Senior administrator")};
                var buttons=new List<Button>();
                void Select(int value){level=value;foreach(var b in buttons)SetNavState(b,Equals(b.Tag,value));ConfirmationDeleteButton.IsEnabled=level!=user.AdminLevel;}
                for(var i=0;i<labels.Length;i++)
                {
                    var value=i;var b=SocialButton(labels[i],()=>{Select(value);return Task.CompletedTask;});
                    b.Tag=i;b.HorizontalAlignment=HorizontalAlignment.Stretch;b.HorizontalContentAlignment=HorizontalAlignment.Left;b.Margin=new Thickness(0,0,0,7);b.Foreground=SocialBrush("#F1F5FC");
                    buttons.Add(b);choices.Children.Add(b);
                }
                ConfirmationChangesPanel.Children.Add(choices);Select(level);
                LauncherIcon.SetKind(ConfirmationDeleteButton,IconKind.Shield);ConfirmationActionIcon.Kind=IconKind.Shield;
                ConfirmationIconBadge.Background=SocialBrush("#43391F");ConfirmationIconBadge.BorderBrush=SocialBrush("#907741");ConfirmationActionIcon.Foreground=SocialBrush("#F2D389");
                ConfirmationDeleteButton.Background=SocialBrush("#80662F");ConfirmationDeleteButton.BorderBrush=SocialBrush("#D5AE52");
                Motion.SetHoverBackground(ConfirmationDeleteButton,SocialBrush("#A3833D"));Motion.SetPressedBackground(ConfirmationDeleteButton,SocialBrush("#695425"));
            }
        }
        if(!await pending||owner!=_account.UserId)return;
        // Compute relative duration at confirmation, not when the dialog first opened.
        if(action=="ban"&&permanent.IsChecked!=true)
        {
            if(!ModerationDuration.TryDeadline(DateTimeOffset.UtcNow,durationFields[0].Text,durationFields[1].Text,durationFields[2].Text,out var parsed))return;
            end=parsed;
        }
        var reasonValue=reason.Text.Trim();var deadline=action=="ban"&&permanent.IsChecked!=true?end:null;int? selectedRole=action=="role"?level:null;
        await RunAdminMutationAsync(()=>ActivityStore.IsSmokeTest&&_adminActionOverride is not null?_adminActionOverride(action,user.Id,reasonValue,deadline,selectedRole):
            _account.AdminActionAsync(action,user.Id,reasonValue,deadline,selectedRole,_accountLifetime.Token));
    }
    private async Task RunAdminMutationAsync(Func<Task> action)
    {
        if(_adminBusy||_account.AdminLevel<1)return;var owner=_account.UserId;_adminBusy=true;
        if(_adminRows is not null)_adminRows.IsEnabled=false;
        ShowToast(()=>T("Сохраняем изменения…","Saving changes…"));
        try{await action();if(owner==_account.UserId){ShowToast(()=>T("Изменения сохранены.","Changes saved."));await LoadAdminAsync();await RefreshSocialAsync();}}
        catch(AccountException e){if(owner==_account.UserId)ShowToast(()=>AccountMessage(e.Code),true);}
        catch(OperationCanceledException){}
        catch{if(owner==_account.UserId)ShowToast(()=>T("Не удалось подтвердить действие. Обновите список.","Could not confirm the action. Refresh the list."),true);}
        finally{_adminBusy=false;if(_adminRows is not null)_adminRows.IsEnabled=true;}
    }
    private async Task OpenAdminProfileAsync(Guid id)
    {
        var owner=_account.UserId;
        await RunAdminReadAsync(async()=>{var player=await _account.GetPlayerProfileAsync(id,_accountLifetime.Token);if(_account.AdminLevel<1||owner!=_account.UserId)return;_adminViewedPlayer=player;ShowSocialDetails(player);});
    }
    private async Task OpenAdminChatAsync(Guid id)
    {
        var owner=_account.UserId;
        await RunAdminReadAsync(async()=>{await _account.StartAdminChatAsync(id,_accountLifetime.Token);if(owner!=_account.UserId||_account.AdminLevel<1)return;await RefreshSocialAsync();if(owner!=_account.UserId||_account.AdminLevel<1)return;var player=_socialPlayers.FirstOrDefault(p=>p.Id==id);if(player is not null){SetActivePage("friends");_socialSection="chats";if(_socialPeer!=id)await OpenSocialChatAsync(player);}});
    }
    private Task AdminAddFriendAsync(AdminPlayer user)
    {
        var owner=_account.UserId;
        return RunAdminReadAsync(async()=>{await _account.FriendActionAsync("request",nickname:user.Nickname,ct:_accountLifetime.Token);if(owner!=_account.UserId||_account.AdminLevel<1)return;ShowToast(()=>T("Заявка отправлена.","Friend request sent."));await RefreshSocialAsync();});
    }
    private async Task RunAdminReadAsync(Func<Task> work)
    {
        if(_account.AdminLevel<1||_adminBusy||ConfirmationActive)return;
        var owner=_account.UserId;
        try{await work();}catch(AccountException e){if(owner==_account.UserId)ShowToast(()=>AccountMessage(e.Code),true);}catch(OperationCanceledException){}catch{if(owner==_account.UserId)ShowToast(()=>T("Не удалось выполнить действие.","Could not complete action."),true);}
    }
}
