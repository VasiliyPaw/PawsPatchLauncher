using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
namespace PawsPatchLauncher;
public sealed partial class AccountService
{
 private SocialOffer ReadOffer(JsonElement json,Guid? peer=null)
 {
  var offer=json.Deserialize<SocialOffer>()??throw new AccountException("invalid_response");
  if(!Guid.TryParse(UserId,out var owner))throw new AccountException("session_expired");
  offer.Validate(owner,peer);return offer;
 }
 public Task<SocialOffer> CreateOfferAsync(Guid target,Guid id,string? code,SaveTransferDescriptor? save,CancellationToken ct=default)
 {
  if(code is not null && !FriendConfiguration.TryParse(code,code.StartsWith("PAW-BETA-")?"beta":"stable",out _))throw new AccountException("invalid_offer");
  if(save is not null)SaveTransferGuard.ValidateDescriptor(save);
  return SocialRpcAsync("paw_offer_create",new{target,offer_id=id,offer_kind=save is null?"config":"save",configuration=code,file_name=save?.FileName,file_size=save?.Size,sha256=save?.Sha256},
   json=>ReadOffer(json.GetProperty("offer"),target),ct);
 }
 public Task<IReadOnlyList<SocialOffer>> GetOffersAsync(Guid target,CancellationToken ct=default)
  =>SocialRpcAsync<IReadOnlyList<SocialOffer>>("paw_offers",new{target},json=>{
   var items=json.GetProperty("offers");if(items.GetArrayLength()>50)throw new AccountException("invalid_response");
   return items.EnumerateArray().Select(o=>ReadOffer(o,target)).ToArray();
  },ct);
 public Task<SocialOffer> OfferActionAsync(Guid id,string action,Guid? attempt=null,CancellationToken ct=default)
 {
  if(action is not ("begin" or "decline" or "touch" or "complete" or "fail" or "cancel"))throw new ArgumentException("Invalid offer action.");
  return SocialRpcAsync("paw_offer_action",new{offer_id=id,action,attempt},json=>ReadOffer(json.GetProperty("offer")),ct);
 }
 public Task<IReadOnlyList<SocialOffer>> GetOfferStatesAsync(Guid target,IReadOnlyList<Guid> ids,CancellationToken ct=default)
 {
  if(target==Guid.Empty||ids.Count is <1 or >200||ids.Any(id=>id==Guid.Empty)||ids.Distinct().Count()!=ids.Count)
   throw new AccountException("invalid_offer");
  return SocialRpcAsync<IReadOnlyList<SocialOffer>>("paw_read_offer_states",new{target,offer_ids=ids},json=>{
   var values=json.GetProperty("offers");if(values.GetArrayLength()>ids.Count)throw new AccountException("invalid_response");
   var offers=values.EnumerateArray().Select(o=>ReadOffer(o,target)).ToArray();
   if(offers.Any(o=>!ids.Contains(o.Id))||offers.Select(o=>o.Id).Distinct().Count()!=offers.Length)throw new AccountException("invalid_response");
   return offers;
  },ct);
 }
 public Task CleanupTransfersAsync(CancellationToken ct=default)=>WithAccountAsync(async()=>{
  using var result=await RequestAsync(HttpMethod.Post,"social-transfers?action=cleanup",null,_session!.AccessToken,ct,portal:true);
 },ct);
 public async Task<byte[]> TransferSaveAsync(Guid offer,string action,byte[]? upload=null,CancellationToken ct=default)
 {
  if(offer==Guid.Empty||action is not ("upload" or "download")||upload?.Length>SaveTransferGuard.MaximumBytes)throw new AccountException("invalid_save");
  var snapshot=upload is null?null:(byte[])upload.Clone();byte[] bytes=[];
  await WithAccountAsync(async()=>{
   using var request=new HttpRequestMessage(HttpMethod.Post,ProjectUrl+"/functions/v1/social-transfers?action="+action+"&offer_id="+offer);
   request.Headers.Add("apikey",PublishableKey);request.Headers.Add("x-paw-launcher",_launcherId.ToString());
   request.Headers.Authorization=new AuthenticationHeaderValue("Bearer",_session!.AccessToken);
   if(snapshot is not null){request.Content=new ByteArrayContent(snapshot);request.Content.Headers.ContentType=new("application/octet-stream");}
   using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(TimeSpan.FromMinutes(3));
   try {
    using var response=await _http.SendAsync(request,HttpCompletionOption.ResponseHeadersRead,timeout.Token).ConfigureAwait(false);
    await using var source=await response.Content.ReadAsStreamAsync(timeout.Token).ConfigureAwait(false);
    using var output=new MemoryStream();var buffer=new byte[65536];int count;
    var max=response.IsSuccessStatusCode&&action=="download"?SaveTransferGuard.MaximumBytes:65536;
    while((count=await source.ReadAsync(buffer,timeout.Token).ConfigureAwait(false))!=0){if(output.Length+count>max)throw new AccountException("invalid_response");output.Write(buffer,0,count);}
    bytes=output.ToArray();
    if(action=="download"&&response.IsSuccessStatusCode&&response.Content.Headers.ContentType?.MediaType=="application/octet-stream")return;
    using var json=JsonDocument.Parse(bytes);var status=Text(json.RootElement,"status");
    if(response.IsSuccessStatusCode&&status=="ok")return;
    throw new AccountException(status is "session_replaced" or "session_expired" or "unauthorized" or "offer_unavailable" or "invalid_save"?status:"network");
   }catch(HttpRequestException){throw new AccountException("network");}
   catch(OperationCanceledException) when(!ct.IsCancellationRequested){throw new AccountException("network");}
  },ct);
  return bytes;
 }
}
