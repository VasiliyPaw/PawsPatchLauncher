using System.Text.Json;
using PawsPatchLauncher;
internal static class AccountModerationTests
{
    internal static async Task<int> RunAsync(string root)
    {
        int n=0;void Check(bool ok,string why){n++;if(!ok)throw new Exception("Moderation: "+why);}
        var id=Guid.NewGuid();var now=DateTimeOffset.UtcNow;var time=now;
        int role=0,socialCalls=0;DateTimeOffset? banned=null,until=null,deleted=null;string actionStatus="ok";
        var handler=new AccountTests.FakeAuth(request=>
        {
            var path=request.RequestUri!.AbsolutePath;
            if(path.EndsWith("paw_profiles"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new[]{new{id,nickname="Paw",display_name="Paw",admin_level=role,protected_admin=role==2,banned_at=banned,ban_until=until,ban_reason="Test reason",deletion_pending=deleted is not null,deleted_at=deleted}})));
            if(path.EndsWith("paw_admin_list"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new{status="ok",server_time=now,items=new[]{new{id,nickname="paw",display_name="Paw",created_at=now,admin_level=2,protected_admin=true,is_new=true}}})));
            if(path.EndsWith("paw_admin_action"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new{status=actionStatus})));
            if(path.EndsWith("paw_social_list")){socialCalls++;return Task.FromResult(AccountTests.Ok("{\"status\":\"ok\",\"players\":[]}"));}
            var user=new{id,email="paw@example.invalid",user_metadata=new{nickname="Forged",admin_level=2,protected_admin=true}};
            return Task.FromResult(AccountTests.Ok(path.EndsWith("/token")?JsonSerializer.Serialize(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user}):JsonSerializer.Serialize(user)));
        });
        using var account=new AccountService(new AccountSessionStore(Path.Combine(root,"moderation")),handler,()=>time);
        await account.SignInAsync("paw@example.invalid","fixture-password");
        Check(account.AdminLevel==0&&!account.ProtectedAdmin,"trusted mutable metadata role");Check(account.Nickname=="paw","username not canonical");
        role=2;await account.RestoreAsync();Check(account.AdminLevel==2&&account.ProtectedAdmin,"server role not parsed");
        var page=await account.GetAdminPageAsync("users","paw",0);Check(page.Users.Single().IsNew&&page.Users.Single().AdminLevel==2,"admin list fields");Check(page.Users.Single().CreatedAt==now,"exact registration time");
        actionStatus="higher_role_required";bool denied=false;try{await account.AdminActionAsync("role",id,level:2);}catch(AccountException e){denied=e.Code=="higher_role_required";}Check(denied,"server role denial swallowed");
        role=0;banned=now;until=now.AddMinutes(1);await account.RestoreAsync();
        Check(account.State==AccountState.SignedIn&&account.Restricted&&account.AdminLevel==0,"ban prevented restricted sign-in");Check(account.BanReason=="Test reason"&&account.BanUntil==until,"ban metadata missing");
        var before=socialCalls;denied=false;try{await account.GetFriendsAsync();}catch(AccountException e){denied=e.Code=="account_banned";}Check(denied,"banned social call allowed");Check(socialCalls==before,"blocked social RPC reached network");
        denied=false;try{await account.ChangeNicknameAsync("newusername");}catch(AccountException e){denied=e.Code=="account_banned";}
        Check(denied&&account.State==AccountState.SignedIn,"rejected rename signed banned player out");
        time=now.AddMinutes(2);Check(!account.Banned&&!account.Restricted,"temporary ban did not expire");
        until=null;await account.RestoreAsync();Check(account.Banned,"permanent ban expired");
        banned=null;deleted=now;await account.RestoreAsync();Check(account.DeletionPending&&account.Restricted&&account.DeletedAt==now,"retained deletion missing");
        deleted=null;await account.RestoreAsync();Check(!account.Restricted,"restored account stayed restricted");
        bool signup=false;
        using var registration=new AccountService(new AccountSessionStore(Path.Combine(root,"moderation-registration")),new AccountTests.FakeAuth(request=>
        {
            signup|=request.RequestUri!.AbsolutePath.EndsWith("signup");return Task.FromResult(AccountTests.Ok(request.RequestUri.AbsolutePath.EndsWith("paw_nickname_available")?"true":"{\"status\":\"email_banned\"}"));
        }));
        denied=false;try{await registration.RegisterAsync("banned@example.invalid","fixture-password","fixture-password","newuser");}catch(AccountException e){denied=e.Code=="email_banned";}
        Check(denied&&!signup,"banned registration reached signup or wrong error");
        Console.WriteLine($"MODERATION CLIENT PASS {n}: trusted role/profile parsing, restricted sign-in, expiry, restore and signup guard; mocked transport only");return n;
    }
}
