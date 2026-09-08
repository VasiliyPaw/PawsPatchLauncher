using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using System.Buffers.Binary;
using PawsPatchLauncher;
internal static class SocialIdentityMediaTests
{
 internal static async Task<int> RunAsync(string root)
 {
  int count=0;
  void Check(bool ok,string why){count++;if(!ok)throw new Exception("Social identity/media: "+why);}
  void Reject(Action f){try{f();}catch(Exception e) when(e is AccountException or InvalidDataException){count++;return;}throw new Exception("Expected rejection");}
  foreach(var name in new[]{"A","Common name","Игрок 🐾","Same display"}){AccountService.ValidateDisplayName(name);count++;}
  foreach(var name in new[]{""," "," name","name ","a\nb","a\u200bb",new string('a',33)})Reject(()=>AccountService.ValidateDisplayName(name));
  var id=Guid.NewGuid();var display="Same display";int usernameCalls=0,emailCalls=0;
  var store=new AccountSessionStore(Path.Combine(root,"identity-media"));
  using(var account=new AccountService(store,new Mock(async request=>{
   var path=request.RequestUri!.AbsolutePath;var user=new{id,email="private@example.invalid"};
   if(path.EndsWith("username-login")){
    using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
    Check(body.RootElement.GetProperty("username").GetString()=="unique_1","username transport must normalize uppercase input");
    Check(!body.RootElement.TryGetProperty("email",out _),"username login exposes email before authentication");usernameCalls++;
    return Ok(new{status="ok",access_token="access",refresh_token="refresh",expires_in=3600,user});
   }
   if(path.EndsWith("/token")){emailCalls++;return Ok(new{access_token="access",refresh_token="refresh",expires_in=3600,user});}
   if(path.EndsWith("/user"))return Ok(user);
   if(path.EndsWith("paw_launcher_session"))return Ok(new{status="ok"});
   if(path.EndsWith("paw_profiles"))return Ok(new[]{new{id,nickname="Unique_1",display_name=display}});
   if(path.EndsWith("paw_change_display_name")){
    Check(request.Headers.Contains("x-paw-launcher"),"name mutation missing active instance guard");
    using var body=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());display=body.RootElement.GetProperty("candidate").GetString()!;
    return Ok(new{status="ok"});
   }
   throw new Exception(path);
  }))){
   await account.SignInAsync("@Unique_1","secret6");Check(usernameCalls==1&&emailCalls==0,"username routing");
   Check(account.Nickname=="unique_1"&&account.DisplayName=="Same display","separate identity fields");
   await account.ChangeDisplayNameAsync("Another display");Check(account.Nickname=="unique_1"&&account.DisplayName=="Another display","name change mutated identifier");
   await account.SignInAsync("private@example.invalid","secret6");Check(emailCalls==1,"email login regression");
  }
  using(var register=new AccountService(new AccountSessionStore(Path.Combine(root,"identity-signup")),new Mock(async req=>{
   if(req.RequestUri!.AbsolutePath.EndsWith("paw_nickname_available"))return Ok(true);
   if(req.RequestUri.AbsolutePath.EndsWith("paw_registration_check"))return Ok(new{status="ok"});
   using var body=JsonDocument.Parse(await req.Content!.ReadAsStringAsync());var data=body.RootElement.GetProperty("data");
   Check(data.GetProperty("nickname").GetString()=="unique_2"&&data.GetProperty("display_name").GetString()=="Same display","registration metadata");
   return Ok(new{user=new{id}});
  }))){
   Check(!await register.RegisterAsync("new@example.invalid","secret6","secret6","Unique_2",displayName:"Same display"),"unconfirmed signup treated as signed in");
  }
  Check(AccountService.NormalizeUsername("Paw_ЁЖ-Я123")=="paw_ёж-я123","Latin and Cyrillic invariant lowercase");
  foreach(var bits in new[]{8,16,24,32}){
   int step=bits/8;var wav=new byte[44+step*2];
   "RIFF"u8.CopyTo(wav);BinaryPrimitives.WriteInt32LittleEndian(wav.AsSpan(4),wav.Length-8);"WAVEfmt "u8.CopyTo(wav.AsSpan(8));
   BinaryPrimitives.WriteInt32LittleEndian(wav.AsSpan(16),16);BinaryPrimitives.WriteInt16LittleEndian(wav.AsSpan(20),1);BinaryPrimitives.WriteInt16LittleEndian(wav.AsSpan(22),1);
   BinaryPrimitives.WriteInt32LittleEndian(wav.AsSpan(24),8000);BinaryPrimitives.WriteInt32LittleEndian(wav.AsSpan(28),8000*step);
   BinaryPrimitives.WriteInt16LittleEndian(wav.AsSpan(32),(short)step);BinaryPrimitives.WriteInt16LittleEndian(wav.AsSpan(34),(short)bits);
   "data"u8.CopyTo(wav.AsSpan(36));BinaryPrimitives.WriteInt32LittleEndian(wav.AsSpan(40),step*2);
   wav[44]=bits==8?(byte)200:(byte)80;wav[44+step]=bits==8?(byte)56:(byte)160;
   var original=(byte[])wav.Clone();Check(NotificationAudio.WithVolume(wav,1).SequenceEqual(wav),"100 percent changed PCM");
   var silent=NotificationAudio.WithVolume(wav,0);Check(silent.Skip(44).All(b=>b==(bits==8?128:0)),"zero not silent");
   var half=NotificationAudio.WithVolume(wav,.5);Check(half[44]==(bits==8?164:40),"half volume");Check(wav.SequenceEqual(original),"input WAV mutated");
  }
  Check(new UserSettings().NotificationVolume==100,"legacy volume default");
  foreach(var address in new[]{"127.0.0.1","10.1.2.3","192.168.1.1","172.16.0.1","169.254.169.254","100.64.0.1","::1","fc00::1","fe80::1","::ffff:127.0.0.1","2001:db8::1"})Check(!ChatMedia.IsPublic(IPAddress.Parse(address)),"private address accepted");
  foreach(var address in new[]{"8.8.8.8","1.1.1.1","2606:4700:4700::1111"})Check(ChatMedia.IsPublic(IPAddress.Parse(address)),"public address rejected");
  Check(ChatMedia.Find("https://media.discordapp.net/attachments/1/a.gif?ex=x&hm=y").Count==1,"GIF query string lost");
  const string loadedLink="https://media.discordapp.net/attachments/1/a.gif?ex=x&hm=y";
  var loaded=new HashSet<string>{loadedLink};
  Check(ChatMedia.WithoutLoadedLinks(loadedLink,loaded)=="","loaded-only media link not hidden");
  Check(ChatMedia.WithoutLoadedLinks("Look\n"+loadedLink,loaded)=="Look","caption lost");
  Check(ChatMedia.WithoutLoadedLinks(loadedLink+"2",loaded)==loadedLink+"2","URL prefix removed another signature");
  Check(ChatMedia.WithoutLoadedLinks("  "+loadedLink,new HashSet<string>())=="  "+loadedLink,"failed/unloaded link altered");
  Check(ChatMedia.WithoutLoadedLinks(loadedLink+" "+loadedLink,loaded)=="","duplicate loaded URI retained");
  Check(ChatMedia.WithoutLoadedLinks(loadedLink+" https://example.com/b.png",loaded)=="https://example.com/b.png","unloaded second image hidden");
  Check(ChatMedia.WithoutLoadedLinks("See "+loadedLink+".",loaded)=="See .","trailing punctuation changed");
  Check(ChatMedia.Find("http://a.com/a.png https://127.0.0.1/a.gif https://user:pass@example.com/a.png https://example.com:8443/a.png").Count==0,"unsafe media URL");
  Check(ChatMedia.Automatic(new Uri("https://media.discordapp.net/a.gif"))&&!ChatMedia.Automatic(new Uri("https://media.discordapp.net.evil.com/a.gif")),"automatic host suffix bypass");
  var gif=Convert.FromBase64String("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==");
  ChatMedia.ValidateContainer(gif);count++;Reject(()=>ChatMedia.ValidateContainer(gif[..^1]));
  int downloads=0;
  using(var media=new ChatMedia(new Mock(req=>{
   downloads++;Check(req.Headers.Authorization is null&&!req.Headers.Contains("Cookie"),"credentials sent to media origin");
   return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){Content=new ByteArrayContent(gif)});
  }))){
   var uri=new Uri("https://media.discordapp.net/test.gif?private-query=yes");
   Check((await media.LoadAsync(uri,default)).SequenceEqual(gif),"media bytes");
   await media.LoadAsync(uri,default);Check(downloads==1,"memory cache duplicate download");
  }
  using(var media=new ChatMedia(new Mock(_=>{
   var res=new HttpResponseMessage(HttpStatusCode.Redirect);res.Headers.Location=new Uri("https://127.0.0.1/private.gif");return Task.FromResult(res);
  }))){
   bool denied=false;try{await media.LoadAsync(new Uri("https://example.com/test.gif"),default);}catch(InvalidDataException){denied=true;}
   Check(denied,"private redirect");
  }
  var huge=(byte[])gif.Clone();huge[6]=255;huge[7]=255;Reject(()=>ChatMedia.ValidateContainer(huge));
  Reject(()=>ChatMedia.CheckDimensions(4096,4096));Reject(()=>ChatMedia.ValidateContainer("<html>invalid image</html>"u8.ToArray()));
  var saves=Path.Combine(root,"game-running-save");Directory.CreateDirectory(saves);
  var bytes=new byte[16];"TGCK"u8.CopyTo(bytes);var save=SaveTransferGuard.Describe("test.rsg",bytes);
  var result=await SaveTransferGuard.InstallAsync(saves,save,bytes,null,()=>true,allowWhileRunning:true);
  Check(File.ReadAllBytes(result.Path).SequenceEqual(bytes),"receive while game running");
  var hash=Convert.ToHexString(SHA256.HashData(bytes));bytes[8]=1;save=SaveTransferGuard.Describe("test.rsg",bytes);
  using(var gameWrite=new FileStream(result.Path,FileMode.Open,FileAccess.Write,FileShare.Read)){
   bool rejected=false;try{await SaveTransferGuard.InstallAsync(saves,save,bytes,hash,()=>true,allowWhileRunning:true);}catch(IOException){rejected=true;}
   Check(rejected,"active game write overwritten");
  }
  result=await SaveTransferGuard.InstallAsync(saves,save,bytes,hash,()=>true,allowWhileRunning:true);
  Check(result.BackupPath is not null&&Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(result.BackupPath)))==hash,"running-game overwrite backup");
  Console.WriteLine($"IDENTITY + MEDIA PASS {count}: username/password, display metadata, PCM volume, media boundaries, game-running save lock and backup; mocked Auth, no network/media download");
  return count;
 }
 private static HttpResponseMessage Ok(object value)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(value))};
 private sealed class Mock(Func<HttpRequestMessage,Task<HttpResponseMessage>> handler):HttpMessageHandler{
  protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>handler(request);
 }
}
