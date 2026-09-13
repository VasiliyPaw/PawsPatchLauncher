using System.Net;
using System.Text.Json;
using PawsPatchLauncher;

public static class SocialVersionTests
{
    public static async Task<int> RunAsync(string root)
    {
        var count=0;
        void Check(bool ok,string why){count++;if(!ok)throw new Exception("Social versions: "+why);}
        foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})
        foreach(var channelName in new[]{"stable","beta"})
        {
            var settings=new UserSettings {Mod=mod,Channel=channelName,RussianLocalization=false,GameVoiceLanguage="en"};
            GameMod.SetPawPatch(settings,true);
            var channel=new ChannelManifest {Channel=channelName,Packages=[
                new(){Id="arcane-wars",Version="1",Mods=[GameMod.ArcaneWars]},
                new(){Id="pawpatch-core",Version="0.3.0-beta.2",Mods=[GameMod.ArcaneWars]},
                new(){Id="immortals",Version="2.1",Mods=[GameMod.Immortals]},
                new(){Id="pure-fixes-data",Version="0.1.0",Mods=[GameMod.Vanilla,GameMod.Immortals]},
                new(){Id="game-voice-ru",Version="1",Mods=[GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars]} ]};
            var catalog=FriendVersionCatalog.Create(channel,"0.6.4");
            var peer=new SocialPlayer(Guid.NewGuid(),"player","friend",Channel:channelName,Configuration:FriendConfiguration.Create(settings),
                Versions:new SocialVersions("0.6.4.0",mod,channelName,catalog.ContentIds[mod],PawPatchVersions.ForChannel(channel,mod)));
            Check(PeerVersionPolicy.Check(peer,catalog)==PeerVersionStatus.Current,"matching versions blocked");
            Check(PeerVersionPolicy.Check(peer with {Versions=peer.Versions! with {Launcher="0.6.3"}},catalog)==PeerVersionStatus.OldLauncher,"old launcher accepted");
            Check(PeerVersionPolicy.Check(peer with {Versions=peer.Versions! with {ContentId=new string('0',64)}},catalog)==PeerVersionStatus.OldPatch,"old mod release accepted");
            Check(PeerVersionPolicy.Check(peer with {Versions=peer.Versions! with {Launcher="0.6.3",ContentId=new string('0',64)}},catalog)==PeerVersionStatus.OldLauncherAndPatch,"combined warning missing");
            Check(PeerVersionPolicy.Check(peer with {Versions=null},catalog)==PeerVersionStatus.Unknown,"legacy client accepted");
            Check(PeerVersionPolicy.Check(peer with {Versions=peer.Versions! with {Patch="0.0.1"}},catalog)==PeerVersionStatus.OldPatch,"old patch version accepted despite matching content identity");
            Check(PeerVersionPolicy.Check(peer with {Versions=peer.Versions! with {Patch=null}},catalog)==PeerVersionStatus.Unknown,"missing enabled patch version accepted");
            Check(PeerVersionPolicy.Check(peer,null)==PeerVersionStatus.Checking,"no catalog marked latest");
            Check(PeerVersionPolicy.Check(peer with {Versions=peer.Versions! with {Launcher="0.6.5"}},catalog)==PeerVersionStatus.Current,"newer launcher called old");
            Check(PeerVersionPolicy.Check(peer with {Versions=peer.Versions! with {Channel=channelName=="beta"?"stable":"beta"}},catalog)==PeerVersionStatus.Unknown,"other channel versions accepted");
            var other=JsonSerializer.Deserialize<ChannelManifest>(JsonSerializer.Serialize(channel))!;
            other.Packages.First(p=>!ModLibrary.BelongsTo(p,mod)&&!GameLanguages.IsLanguage(p)).Version="9";
            Check(PeerVersionPolicy.Check(peer,FriendVersionCatalog.Create(other,"0.6.4"))==PeerVersionStatus.Current,"unrelated mod update blocked peer");
            other.Packages.First(p=>p.Id=="game-voice-ru").Version="10";
            Check(PeerVersionPolicy.Check(peer,FriendVersionCatalog.Create(other,"0.6.4"))==PeerVersionStatus.Current,"localization update blocked gameplay copy");
            var state=new InstallState {AppliedSettings=settings,ReleaseId=ChannelFingerprint.Create(channel)};
            var published=SocialVersions.Installed(state,channel,"0.6.4.0");
            Check(published.ContentId==catalog.ContentIds[mod] && published.Mod==mod,"presence published selected rather than applied release");
            Check(SocialVersions.Installed(state,null,"0.6.4.0").ContentId is null,"missing archive invented current patch");
            state.ReleaseId=new string('F',64);
            Check(SocialVersions.Installed(state,channel,"0.6.4.0").ContentId is null,"different archive accepted as installed");
        }
        foreach(var invalid in new[]{"null","[]","{}","{\"launcher\":4}","{\"launcher\":\"x\"}","{\"launcher\":\"0.6.4\",\"content_id\":\"bad\"}"})
            Check(SocialVersions.Read(JsonDocument.Parse(invalid).RootElement) is null,"invalid metadata accepted");
        var owner=Guid.NewGuid();var peerId=Guid.NewGuid();var versions=new SocialVersions("0.6.4.0",GameMod.Vanilla,"stable",new string('A',64),"0.1.0");
        foreach(var oldServer in new[]{false,true})
        {
            var calls=0;
            using var service=new AccountService(new AccountSessionStore(Path.Combine(root,"versions-"+Guid.NewGuid())),new Mock(async request=>
            {
                var path=request.RequestUri!.AbsolutePath;
                if(path.EndsWith("/token"))return Json(new{access_token="test",refresh_token="refresh",expires_in=3600,user=new{id=owner,email="fixture@example.invalid"}});
                if(path.EndsWith("paw_profiles"))return Json(new[]{new{id=owner,nickname="fixture"}});
                if(path.EndsWith("paw_launcher_session"))return Json(new{status="ok"});
                if(path.EndsWith("paw_presence"))
                {
                    calls++;using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                    var components=body.RootElement.GetProperty("components");
                    Check(components.GetProperty("core").GetBoolean(),"component flags lost");
                    if(calls==1)
                    {
                        var sent=SocialVersions.Read(components.GetProperty("_versions"));
                        Check(sent==versions,"version envelope transport changed");
                        return Json(new{status=oldServer?"invalid_presence":"ok"});
                    }
                    Check(!components.TryGetProperty("_versions",out _),"old-server retry retained version envelope");return Json(new{status="ok"});
                }
                if(path.EndsWith("paw_social_list"))return Json(new{status="ok",players=new[]{new{id=peerId,nickname="peer",relation="friend",channel="stable",configuration="PAW-STABLE-VANILLA-PP1",versions=oldServer?null:versions}}});
                throw new Exception("Unexpected mock route "+path);
            }));
            await service.SignInAsync("fixture@example.invalid","fixture-password",remember:false);
            await service.PublishConfigurationPresenceAsync(false,"stable",new Dictionary<string,bool>{{"core",true}},"PAW-STABLE-VANILLA-PP1",versions:versions);
            Check(calls==(oldServer?2:1),"unexpected presence retry count");
            var players=await service.GetFriendsAsync();
            Check(players.Single().Versions==(oldServer?null:versions),"peer metadata parse mismatch");
        }
        Console.WriteLine($"SOCIAL VERSION POLICY/TRANSPORT PASS {count}");return count;
    }
    private static HttpResponseMessage Json(object data)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(data))};
    private sealed class Mock(Func<HttpRequestMessage,Task<HttpResponseMessage>> action):HttpMessageHandler
    {protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken cancellationToken)=>action(request);}
}
