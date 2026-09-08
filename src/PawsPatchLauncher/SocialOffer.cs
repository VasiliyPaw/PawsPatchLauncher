using System.Text.Json.Serialization;
namespace PawsPatchLauncher;
public sealed record SocialOffer(
 [property:JsonPropertyName("id")] Guid Id,
 [property:JsonPropertyName("sender_id")] Guid Sender,
 [property:JsonPropertyName("recipient_id")] Guid Recipient,
 [property:JsonPropertyName("kind")] string Kind,
 [property:JsonPropertyName("configuration")] string? Configuration,
 [property:JsonPropertyName("file_name")] string? FileName,
 [property:JsonPropertyName("file_size")] long? FileSize,
 [property:JsonPropertyName("sha256")] string? Sha256,
 [property:JsonPropertyName("state")] string State,
 [property:JsonPropertyName("created_at")] DateTimeOffset CreatedAt,
 [property:JsonPropertyName("expires_at")] DateTimeOffset ExpiresAt,
 [property:JsonPropertyName("attempt")] Guid? Attempt,
 [property:JsonPropertyName("apply_until")] DateTimeOffset? ApplyUntil)
{
 public SaveTransferDescriptor Save => new(FileName!,FileSize??0,Sha256!);
 public string Channel => Configuration?.StartsWith("PAW-BETA-",StringComparison.Ordinal)==true?"beta":"stable";
 public void Validate(Guid owner,Guid? peer=null)
 {
  if(Id==Guid.Empty||Sender==Guid.Empty||Recipient==Guid.Empty||Sender==Recipient||owner!=Sender&&owner!=Recipient
   ||peer is Guid p && p!=Sender && p!=Recipient ||State is not ("uploading" or "pending" or "applying" or "accepted" or "declined" or "failed" or "expired" or "cancelled"))
   throw new AccountException("invalid_response");
  if(Kind=="config"){if(!FriendConfiguration.TryParse(Configuration,Channel,out _))throw new AccountException("invalid_response");}
  else if(Kind=="save")SaveTransferGuard.ValidateDescriptor(Save);
  else throw new AccountException("invalid_response");
 }
}
