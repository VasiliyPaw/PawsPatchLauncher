using System.Text.Json;
using System.Net;
using System.Net.Sockets;
using System.Text;
using PawsPatchLauncher;

internal static class RebornDownloadTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var count=0;void Check(bool ok,string why){if(!ok)throw new Exception("Reborn download: "+why);count++;}
        var now=DateTimeOffset.UtcNow;var storage=new Uri(AccountService.ProjectUrl);
        var build=new RebornBuild(Guid.NewGuid(),"stable","0.23.0",140733219,new('A',64),"KohanReborn-Menu.exe",now,new(),"github","Owner/Private",1458192487,748818121);
        var expiry=now.AddMinutes(50);
        var address=$"https://release-assets.githubusercontent.com/github-production-release-asset/{build.GitHubRepositoryId}/abcd-1234?se={Uri.EscapeDataString(expiry.ToString("O"))}&sig=fixture";
        var valid=new RebornTicket(build,new(address),now.AddMinutes(2),expiry);
        RebornDownloadPolicy.Validate(valid,storage,now);count++;
        var rejected=new[]{
            valid with {Url=new(address.Replace("https:","http:"))},
            valid with {Url=new(address.Replace(".com/",".com:444/"))},
            valid with {Url=new(address.Replace("release-assets.githubusercontent.com","release-assets.githubusercontent.com.evil.invalid"))},
            valid with {Url=new(address.Replace("https://","https://user@"))},
            valid with {Url=new(address+"#fragment")},
            valid with {Url=new(address.Replace("1458192487","1458192488"))},
            valid with {Url=new(address.Replace("abcd-1234","../abcd-1234"))},
            valid with {Url=new(address+"&se="+Uri.EscapeDataString(expiry.ToString("O")))},
            valid with {Url=new(address.Replace("&sig=fixture",""))},
            valid with {UrlExpiresAt=expiry.AddMinutes(1)},
            valid with {ExpiresAt=now},
            valid with {ExpiresAt=now.AddMinutes(4)},
            valid with {UrlExpiresAt=null}
        };
        foreach(var ticket in rejected){try{RebornDownloadPolicy.Validate(ticket,storage,now);throw new Exception("Unsafe ticket accepted");}catch(InvalidDataException){count++;}}
        foreach(var changed in new[]{build with {GitHubAssetId=1},build with {GitHubRepositoryId=1},build with {GitHubRepository="Other/Private"},build with {Executable="Other.exe"}})
            Check(!RebornDownloadPolicy.SameBuild(build,changed),"ticket identity includes GitHub archive and root executable");
        foreach(var changed in new[]{build with {GitHubAssetId=null},build with {GitHubRepositoryId=0},build with {GitHubRepository="../Private"},build with {DownloadProvider="other"},build with {DownloadProvider="supabase"}})
        {try{RebornBuild.Validate(changed);throw new Exception("Unsafe metadata accepted");}catch(InvalidDataException){count++;}}
        var legacy=build with {DownloadProvider="supabase",GitHubRepository=null,GitHubRepositoryId=null,GitHubAssetId=null};
        RebornDownloadPolicy.Validate(new(legacy,new(storage,$"/storage/v1/object/sign/paw-reborn-builds/stable/{build.Id}.zip?token=fixture"),now.AddMinutes(2)),storage,now);count++;
        object Wire(RebornBuild b)=>new{id=b.Id,channel=b.Channel,version=b.Version,size=b.Size,sha256=b.Sha256,executable=b.Executable,published_at=b.PublishedAt,notes=b.Notes,
            download_provider=b.DownloadProvider,github_repository=b.GitHubRepository,github_repository_id=b.GitHubRepositoryId,github_asset_id=b.GitHubAssetId};
        var player=Guid.NewGuid();var mode="valid";var calls=0;
        using var account=new AccountService(new AccountSessionStore(Path.Combine(root,"github-account")),new AccountTests.FakeAuth(request=>
        {
            var path=request.RequestUri!.AbsolutePath;var user=new{id=player,email="reborn@example.invalid"};
            if(path.EndsWith("/token"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user})));
            if(path.EndsWith("/user"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(user)));
            if(path.EndsWith("paw_profiles"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new[]{new{id=player,nickname="reborn",paws_team=true}})));
            if(path.EndsWith("/reborn-builds"))
            {
                calls++;Check(request.RequestUri.Query.Contains("protocol=2")&&request.Headers.Authorization?.Scheme=="Bearer"&&request.Headers.Contains("x-paw-launcher"),"v2 request keeps account and launcher session authentication");
                if(request.RequestUri.Query.Contains("action=catalog"))return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new{status="ok",releases=new[]{Wire(build)}})));
                return Task.FromResult(AccountTests.Ok(JsonSerializer.Serialize(new{status="ok",release=Wire(mode=="substituted"?build with {GitHubAssetId=1}:build),url=address,
                    expires_at=valid.ExpiresAt,url_expires_at=expiry,ticket_version=mode=="legacy"?1:2})));
            }
            throw new Exception("Unexpected GitHub ticket route");
        }));
        await account.SignInAsync("reborn@example.invalid","fixture-password");
        var catalog=await account.GetRebornBuildsAsync();Check(catalog.Count==1&&catalog[0].GitHubAssetId==build.GitHubAssetId,"GitHub catalog metadata parsed");
        var result=await account.GetRebornTicketAsync(catalog[0]);Check(result.Url==valid.Url&&result.UrlExpiresAt==expiry,"upstream expiry distinct from ticket start window");
        foreach(var invalid in new[]{"substituted","legacy"})
        {
            mode=invalid;try{await account.GetRebornTicketAsync(build);throw new Exception("Invalid provider ticket accepted");}
            catch(AccountException error){Check(error.Code=="invalid_response","invalid ticket mapping");}
        }
        Check(calls==4,"unexpected private endpoint calls");
        // Exercise the production downloader over loopback; no account credentials may leave it.
        foreach(var redirect in new[]{false,true})
        {
            var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();
            var endpoint=(IPEndPoint)listener.LocalEndpoint;
            var server=Task.Run(async()=>
            {
                using var peer=await listener.AcceptTcpClientAsync();await using var stream=peer.GetStream();
                var headers=new StringBuilder();var buffer=new byte[1];using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(10));
                while(!headers.ToString().EndsWith("\r\n\r\n",StringComparison.Ordinal)&&headers.Length<8192)
                {if(await stream.ReadAsync(buffer,timeout.Token)==0)break;headers.Append((char)buffer[0]);}
                var response=redirect?"HTTP/1.1 302 Found\r\nContent-Length: 0\r\nLocation: https://evil.invalid/forbidden\r\nConnection: close\r\n\r\n":
                    "HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nabc";
                await stream.WriteAsync(Encoding.ASCII.GetBytes(response),timeout.Token);return headers.ToString();
            });
            try
            {
                var transfer=valid with {Build=build with {Size=3},Url=new($"http://127.0.0.1:{endpoint.Port}/archive")};
                var destination=Path.Combine(root,Guid.NewGuid()+".zip");
                try{await RebornInstall.DownloadAsync(transfer,destination,null,CancellationToken.None);Check(!redirect,"download followed a redirect");}
                catch(System.Net.Http.HttpRequestException){Check(redirect,"ordinary transfer failed");}
                var headers=await server;
                Check(!headers.Contains("Authorization:",StringComparison.OrdinalIgnoreCase)&&!headers.Contains("apikey:",StringComparison.OrdinalIgnoreCase)&&!headers.Contains("Cookie:",StringComparison.OrdinalIgnoreCase),"download must omit account/repository credentials");
                if(!redirect)Check(await File.ReadAllTextAsync(destination)=="abc","download bytes changed");
            }
            finally{listener.Stop();}
        }
        Console.WriteLine($"REBORN GITHUB CLIENT PASS {count}: URL policy, archive identity, v2 transport and independent expiry; no game executed");return count;
    }
}
