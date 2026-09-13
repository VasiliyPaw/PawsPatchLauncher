using System.Net;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class AccountTeamTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var n=0; void Check(bool ok,string why){n++;if(!ok)throw new Exception("Team: "+why);}
        var id=Guid.NewGuid(); bool team=false,banned=false,deleted=false,oldServer=false,network=false; int level=0,missingReads=0; string? mutation=null;
        var handler=new AccountTests.FakeAuth(async request=>
        {
            if(network)throw new HttpRequestException("fixture offline");
            var route=request.RequestUri!.AbsolutePath;
            if(route.EndsWith("paw_profiles"))
            {
                if(oldServer&&request.RequestUri.Query.Contains("paws_team"))
                {
                    missingReads++;
                    return new HttpResponseMessage(HttpStatusCode.BadRequest){Content=new StringContent("{\"code\":\"42703\",\"message\":\"column paw_profiles.paws_team does not exist\"}")};
                }
                return AccountTests.Ok(JsonSerializer.Serialize(new[]{new{id,nickname="teamtest",admin_level=level,paws_team=!oldServer&&team,banned_at=banned?(DateTimeOffset?)DateTimeOffset.UtcNow:null,deletion_pending=deleted}}));
            }
            if(route.EndsWith("paw_admin_action")){mutation=await request.Content!.ReadAsStringAsync();return AccountTests.Ok("{\"status\":\"ok\"}");}
            var user=new{id,email="team@example.invalid",user_metadata=new{nickname="forged",admin_level=2,paws_team=true}};
            return AccountTests.Ok(route.EndsWith("/token")?JsonSerializer.Serialize(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user}):JsonSerializer.Serialize(user));
        });
        var store=new AccountSessionStore(Path.Combine(root,"team-role"));
        using(var service=new AccountService(store,handler))
        {
            Check(!service.CanUseArcaneWars&&!service.PawsTeam,"Guest access");
            await service.SignInAsync("team@example.invalid","fixture-password");
            Check(!service.CanUseArcaneWars&&!service.PawsTeam&&service.AdminLevel==0,"Role trusted from user metadata");
            team=true;await service.RestoreAsync();
            Check(service.PawsTeam&&service.CanUseArcaneWars&&service.AdminLevel==0,"Team parsed as admin or denied");
            Check(store.Read()!.PawsTeam,"Team field not persisted");
            team=false;await service.RestoreAsync();Check(!service.CanUseArcaneWars,"Revoked membership survived refresh");
            foreach(var role in new[]{1,2}){level=role;await service.RestoreAsync();Check(service.CanUseArcaneWars&&!service.PawsTeam,"Admin denied access");}
            level=0;team=true;banned=true;await service.RestoreAsync();Check(!service.CanUseArcaneWars&&!service.PawsTeam,"Banned team access");
            banned=false;deleted=true;await service.RestoreAsync();Check(!service.CanUseArcaneWars,"Deleted team access");
            deleted=false;await service.RestoreAsync();network=true;
            try { await service.RestoreAsync(); } catch(AccountException error) when(error.Code=="network") { }
            Check(!service.CanUseArcaneWars,"Unverified offline role used");
            Check(service.CanUseStoredArcaneWars && !service.PawsTeam && service.AdminLevel == 0,
                "Verified offline member lost local play or gained online authority");
            using (var restarted = new AccountService(store, handler))
            {
                try { await restarted.RestoreAsync(); } catch(AccountException error) when(error.Code=="network") { }
                Check(restarted.State == AccountState.Offline && restarted.CanUseStoredArcaneWars && !restarted.CanUseArcaneWars,
                    "Remembered offline team did not survive restart");
            }
            network=false;await service.RestoreAsync();Check(service.CanUseArcaneWars,"Reverified team denied");
            team=false;await service.RestoreAsync();network=true;
            try { await service.RestoreAsync(); } catch(AccountException error) when(error.Code=="network") { }
            Check(!service.CanUseStoredArcaneWars,"Revoked membership reappeared offline");
            network=false; team=true; await service.RestoreAsync();
            await service.AdminActionAsync("role",id,level:-1);using(var json=JsonDocument.Parse(mutation!))Check(json.RootElement.GetProperty("level").GetInt32()==-1,"Team role RPC encoding");
            await service.SignOutAsync();Check(!service.PawsTeam&&!service.CanUseArcaneWars,"Sign-out retained access");
            Check(!service.CanUseStoredArcaneWars,"Sign-out retained offline access");
        }
        oldServer=true;level=1;team=true;
        using(var legacy=new AccountService(new AccountSessionStore(Path.Combine(root,"team-legacy")),handler))
        {
            await legacy.SignInAsync("team@example.invalid","fixture-password");
            Check(legacy.State==AccountState.SignedIn&&legacy.AdminLevel==1&&!legacy.PawsTeam,"Legacy server login regression");
            await legacy.RestoreAsync();Check(missingReads==1,"Missing team column retried repeatedly");
        }
        using(var json=JsonDocument.Parse(JsonSerializer.Serialize(new{id,nickname="teamtest",relation="friend",paws_team=true,admin_level=0})))
        {var player=AccountService.ReadSocialPlayer(json.RootElement);Check(player.PawsTeam&&player.AdminLevel==0,"Social team badge field");}
        Console.WriteLine($"TEAM ACCOUNT PASS {n}: trusted profile, guest, ordinary user, team, admins, revocation, sign-out, restrictions, offline and legacy server");
        return n;
    }
}
