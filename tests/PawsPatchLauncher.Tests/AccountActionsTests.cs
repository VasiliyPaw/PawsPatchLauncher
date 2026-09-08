using System.Net;
using System.Net.Http;
using System.Text.Json;
using PawsPatchLauncher;
using static AccountTests;
internal static class AccountActionsTests
{
    internal static async Task<int> RunAsync(string root)
    {
        int checks = 0;
        void Check(bool value, string reason) { checks++; if (!value) throw new Exception("Account actions: "+reason); }
        async Task Error(Func<Task> work, string code) { try { await work(); throw new Exception("Expected "+code); } catch(AccountException e) { Check(e.Code==code, e.Code+" vs "+code); } }
        var id=Guid.NewGuid().ToString(); var other=Guid.NewGuid().ToString();
        var vault=new AccountSessionStore(Path.Combine(root,"account-actions"));
        var status="ok"; var deletionCalls=0; var calls=0; string? avatar=null;
        string userId=id;
        using var account=new AccountService(vault,new FakeAuth(async request=>{
            calls++;
            var uri=request.RequestUri!;
            Check(uri.GetLeftPart(UriPartial.Authority)==AccountService.ProjectUrl,"foreign destination");
            Check(request.Headers.GetValues("apikey").Single()==AccountService.PublishableKey,"secret key in client");
            if(uri.AbsolutePath.EndsWith("/token")) return Ok(JsonSerializer.Serialize(new {access_token="test-access",refresh_token="test-refresh",expires_in=3600,user=new {id=userId,email="fixture@example.invalid"}}));
            if(uri.AbsolutePath.Contains("/paw_profiles")) return Ok(JsonSerializer.Serialize(new[]{new {id=userId,nickname="Fixture",email_changed_at=DateTimeOffset.UtcNow, password_changed_at=DateTimeOffset.UtcNow}}));
            if(uri.AbsolutePath.EndsWith("/user")) return Ok(JsonSerializer.Serialize(new{id=userId,email="fixture@example.invalid"}));
            Check(uri.AbsolutePath=="/functions/v1/account-actions","unexpected action endpoint");
            Check(request.Headers.Authorization?.Parameter=="test-access","missing user authentication");
            using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
            var action=body.RootElement.GetProperty("action").GetString();
            if(action=="delete") { deletionCalls++; Check(body.RootElement.GetProperty("confirm").GetString()=="DELETE_MY_ACCOUNT","missing deletion consent"); }
            if(action=="avatar_set") Check(body.RootElement.GetProperty("avatar").GetString()==Convert.ToBase64String(new byte[32]),"upload altered");
            if(action=="avatar_get") return Ok(JsonSerializer.Serialize(new {status,avatar}));
            return new HttpResponseMessage(status=="ok"?HttpStatusCode.OK:HttpStatusCode.Conflict) {Content=new StringContent(JsonSerializer.Serialize(new{status}))};
        }));
        await account.SignInAsync("fixture@example.invalid","secret");
        Check(await account.GetAvatarAsync() is null,"no avatar state");
        avatar=Convert.ToBase64String(new byte[204800]);
        Check((await account.GetAvatarAsync())!.Length==204800,"maximum avatar truncated");
        avatar="not base64";
        await Error(()=>account.GetAvatarAsync(),"invalid_avatar");
        await Error(()=>account.SetAvatarAsync(new byte[204801]),"invalid_avatar");
        await account.SetAvatarAsync(new byte[32]);
        await account.RemoveAvatarAsync();
        status="invalid_credentials";
        await Error(()=>account.DeleteAccountAsync("wrong"),"invalid_credentials");
        Check(account.State==AccountState.SignedIn && File.Exists(vault.SessionPath),"failed deletion cleared sign-in");
        status="outcome_unknown";
        await Error(()=>account.DeleteAccountAsync("secret"),"outcome_unknown");
        Check(account.State==AccountState.SignedIn,"uncertain deletion reported success");
        // Another launcher can replace the protected session. Never apply an action to that new identity.
        var replacement=vault.Read()!; replacement.UserId=other; vault.Save(replacement); userId=other;
        var before=deletionCalls; status="ok";
        await Error(()=>account.DeleteAccountAsync("secret"),"session_expired");
        Check(deletionCalls==before,"deletion crossed account identity");
        await account.SignInAsync("fixture@example.invalid","secret");
        await account.DeleteAccountAsync("secret");
        Check(account.State==AccountState.Guest && !File.Exists(vault.SessionPath),"confirmed deletion retained local sign-in");
        Check(account.Email=="" && account.Nickname=="","deleted profile retained in public state");
        foreach (var remember in new[] {true,false})
        {
            var rotatedVault = new AccountSessionStore(Path.Combine(root,"password-rotation-"+remember));
            using var rotation = new AccountService(rotatedVault,new FakeAuth(r=>
            {
                var path=r.RequestUri!.AbsolutePath;
                var user=JsonSerializer.Serialize(new{id,email="fixture@example.invalid"});
                var fresh="{\"access_token\":\"retained-access\",\"refresh_token\":\"retained-refresh\",\"expires_in\":3600,\"user\":"+user+"}";
                return Task.FromResult(Ok(path.EndsWith("account-actions") ? "{\"status\":\"ok\",\"session\":"+fresh+"}"
                    :path.EndsWith("token")?fresh.Replace("retained-","old-")
                    :path.Contains("paw_profiles")?JsonSerializer.Serialize(new[]{new{id,nickname="Fixture",password_changed_at=DateTimeOffset.UtcNow}}):user));
            }));
            await rotation.SignInAsync("fixture@example.invalid","secret",remember:remember);
            await rotation.ChangePasswordAsync("secret","new-secret","new-secret");
            Check(await rotation.GetAccessTokenAsync()=="retained-access","password change retained revoked old session");
            Check(rotation.Remembered==remember,"password change altered remember choice");
            Check(File.Exists(rotatedVault.SessionPath)==remember,"password change persistence ignored remember");
            if(remember) Check(rotatedVault.Read()!.RefreshToken=="retained-refresh","rotated refresh token not saved");
        }
        Console.WriteLine($"ACCOUNT ACTIONS PASS {checks}: scoped endpoint, private avatar bounds, server errors, deletion and identity isolation");
        return checks;
    }
}
