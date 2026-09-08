using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;
internal static class OfferTests
{
 internal static async Task<int> RunAsync(string root)
 {
  var checks=0;
  void Check(bool value,string why){checks++;if(!value)throw new Exception("Offers: "+why);}
  void Reject(Action action){try{action();}catch(Exception e) when(e is InvalidDataException or AccountException){checks++;return;}throw new Exception("Offers: expected rejection");}
  var audio=NotificationAudio.DefaultBytes();NotificationAudio.Validate(audio);
  Check(Convert.ToHexString(SHA256.HashData(audio))=="98EE0414CFF91D0549689377021E4A485C3FF983CD9DA16DD5046B807D2725D8","user audio changed");
  Reject(()=>NotificationAudio.Validate(new byte[44]));Reject(()=>NotificationAudio.Validate(audio[..20]));
  Reject(()=>NotificationAudio.Validate(new byte[NotificationAudio.MaximumBytes+1]));
  var broken=(byte[])audio.Clone();broken[20]=3;Reject(()=>NotificationAudio.Validate(broken));
  broken=(byte[])audio.Clone();Array.Fill(broken,(byte)255,16,4);Reject(()=>NotificationAudio.Validate(broken));
  var before=new UserSettings();var after=new UserSettings{Channel="beta",RussianLocalization=!before.RussianLocalization,
   IndependentHostility=!before.IndependentHostility,RoamingSpawnMode="standard",AdditionalRoamingCompanies=!before.AdditionalRoamingCompanies,
   SiegeBalance=!before.SiegeBalance,LargeMapSizes=!before.LargeMapSizes,CustomPlayerColors=!before.CustomPlayerColors,
   DesyncMode=before.DesyncMode=="continue"?"stop":"continue",DisablePowersAndShards=!before.DisablePowersAndShards};
  foreach(var ru in new[]{true,false}) {
   var changes=ConfigurationChanges.Describe(before,after,ru);
   Check(changes.Count==10 && changes.All(x=>x.Contains(" → ")),"diff must list all ten changes");
   Check(ConfigurationChanges.Describe(before,before,ru).Count==1,"no-op diff");
   Check(!string.Join("",changes).Contains("C:\\"),"private paths exposed in diff");
   var structured=ConfigurationChanges.Compare(before,after,ru);
   Check(structured.Count==10&&structured.All(c=>c.Before!=c.After),"structured diff contains unchanged settings");
   Check(structured.Select(c=>c.Name+": "+c.Before+" → "+c.After).SequenceEqual(changes),"visual/plain diff mismatch");
   Check(ConfigurationChanges.Compare(before,before,ru).Count==0,"empty structured diff");
  }
  var owner=Guid.NewGuid();var peer=Guid.NewGuid();var outsider=Guid.NewGuid();
  var previous=new[]{new SocialPlayer(peer,"Peer","friend",2)};
  Check(!NotificationAudio.HasNewArrival(previous,previous),"duplicate poll sound");
  Check(NotificationAudio.HasNewArrival(previous,new[]{previous[0] with{Unread=3}}),"message sound missing");
  Check(!NotificationAudio.HasNewArrival(previous,new[]{previous[0] with{Unread=0}}),"read acknowledgement sound");
  Check(NotificationAudio.HasNewArrival(previous,new[]{new SocialPlayer(outsider,"Other","incoming")}),"request sound missing");
  Check(!NotificationAudio.HasNewArrival(previous,new[]{new SocialPlayer(outsider,"Other","outgoing")}),"outgoing request sound");
  var receipt=new OfferReceipt(owner,Guid.NewGuid(),Guid.NewGuid());
  var receipts=new OfferReceiptStore(root);receipts.Save(receipt);
  Check(new OfferReceiptStore(root).Read(owner).Single()==receipt,"interrupted fallback lost after restart");
  receipts.Save(receipt with{Completed=true});
  Check(new OfferReceiptStore(root).Read(owner).Single().Completed,"successful result lost");
  Check(receipts.Read(outsider).Count==0,"receipt leaked between accounts");
  var receiptBytes=File.ReadAllBytes(Path.Combine(root,"account","offer-results",owner.ToString("N"),receipt.Offer.ToString("N")+".dat"));
  Check(!Encoding.UTF8.GetString(receiptBytes).Contains(owner.ToString()),"receipt not protected");
  receipts.Remove(receipt);receipts.Remove(receipt);Check(receipts.Read(owner).Count==0,"receipt removal not idempotent");
  Reject(()=>receipts.Save(receipt with{Owner=Guid.Empty}));
  var key=OfferSendIdentity.Key(owner,peer,"code");var id=OfferSendIdentity.Get(root,key);
  Check(id==OfferSendIdentity.Get(root,key),"restart/retry sends duplicate");
  Check(key!=OfferSendIdentity.Key(outsider,peer,"code")&&key!=OfferSendIdentity.Key(owner,outsider,"code"),"send identity isolation");
  OfferSendIdentity.Complete(root,key);Check(id!=OfferSendIdentity.Get(root,key),"intentional new offer reused completed ID");
  var offer=new SocialOffer(Guid.NewGuid(),owner,peer,"config",ConfigurationCode.Create(before),null,null,null,"pending",DateTimeOffset.UtcNow,DateTimeOffset.UtcNow.AddMinutes(10),null,null);
  offer.Validate(owner,peer);offer.Validate(peer,owner);checks+=2;
  foreach(var invalid in new[]{offer with{Id=Guid.Empty},offer with{Sender=peer},offer with{State="arbitrary"},offer with{Configuration="PAW-INVALID"},offer with{Kind="exec"}})Reject(()=>invalid.Validate(owner,peer));
  Reject(()=>offer.Validate(outsider));Reject(()=>offer.Validate(owner,outsider));
  var bytes=new byte[16];Encoding.ASCII.GetBytes("TGCK").CopyTo(bytes,0);var save=SaveTransferGuard.Describe("fixture.rsg",bytes);
  var saveOffer=offer with{Kind="save",Configuration=null,FileName=save.FileName,FileSize=save.Size,Sha256=save.Sha256};
  saveOffer.Validate(owner,peer);checks++;
  var calls=0;var store=new AccountSessionStore(Path.Combine(root,"offer-account"));
  using var service=new AccountService(store,new Mock(async request=>{
   Check(request.RequestUri!.Host=="trdzsdclscuwwmxnepyt.supabase.co","wrong origin");
   var path=request.RequestUri.AbsolutePath;var user=new{id=owner,email="fixture@example.invalid"};
   if(path.EndsWith("/token"))return Ok(new{access_token="fixture-access",refresh_token="fixture-refresh",expires_in=3600,user});
   if(path.EndsWith("/user"))return Ok(user);
   if(path.EndsWith("paw_profiles"))return Ok(new[]{new{id=owner,nickname="Fixture"}});
   Check(request.Headers.Authorization?.Parameter=="fixture-access"&&request.Headers.Contains("x-paw-launcher"),"missing account/launcher guard");
   if(path.EndsWith("paw_launcher_session"))return Ok(new{status="ok"});
   if(path.EndsWith("paw_offer_create")) {
    using var json=JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
    Check(json.RootElement.GetProperty("offer_id").GetGuid()==offer.Id&&json.RootElement.GetProperty("target").GetGuid()==peer,"wrong immutable identity");
    return Ok(new{status="ok",offer});
   }
   if(path.EndsWith("paw_offers"))return Ok(new{status="ok",offers=new[]{offer}});
   if(path.EndsWith("paw_offer_action"))return Ok(new{status="ok",offer=offer with{State="declined"}});
   if(path.EndsWith("social-transfers")) {
    calls++;if(request.RequestUri.Query.Contains("action=upload")){Check((await request.Content!.ReadAsByteArrayAsync()).SequenceEqual(bytes),"save body corrupted");return Ok(new{status="ok"});}
    if(request.RequestUri.Query.Contains("action=download"))return new HttpResponseMessage(HttpStatusCode.OK){Content=new ByteArrayContent(bytes){Headers={ContentType=new("application/octet-stream")}}};
    return Ok(new{status="ok"});
   }
   throw new Exception("Unexpected offer route: "+path);
  }));
  await service.SignInAsync("fixture@example.invalid","fixture-password");
  Check((await service.CreateOfferAsync(peer,offer.Id,offer.Configuration,null)).Id==offer.Id,"create response");
  Check((await service.GetOffersAsync(peer)).Single()==offer,"list response");
  Check((await service.OfferActionAsync(offer.Id,"decline")).State=="declined","shared response");
  await service.TransferSaveAsync(saveOffer.Id,"upload",bytes);
  Check((await service.TransferSaveAsync(saveOffer.Id,"download")).SequenceEqual(bytes),"download response");
  await service.CleanupTransfersAsync();Check(calls==3,"transport actions");
  Console.WriteLine($"OFFERS PASS {checks}: audio, complete diff, protected receipts, durable send IDs, pair validation, authenticated binary transport");
  return checks;
 }
 private static HttpResponseMessage Ok(object o)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(o),Encoding.UTF8,"application/json")};
 private sealed class Mock(Func<HttpRequestMessage,Task<HttpResponseMessage>> handler):HttpMessageHandler
 {protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>handler(request);}
}
