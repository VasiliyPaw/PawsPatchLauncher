using System.Text.Json;
namespace PawsPatchLauncher;
public sealed record OfferReceipt(Guid Owner,Guid Offer,Guid Attempt,bool Completed=false);
public sealed class OfferReceiptStore(string root)
{
 private string PathFor(Guid owner,Guid offer)=>Path.Combine(root,"account","offer-results",owner.ToString("N"),offer.ToString("N")+".dat");
 public void Save(OfferReceipt receipt)
 {
  if(receipt.Owner==Guid.Empty||receipt.Offer==Guid.Empty||receipt.Attempt==Guid.Empty)throw new InvalidDataException();
  var path=PathFor(receipt.Owner,receipt.Offer);Directory.CreateDirectory(Path.GetDirectoryName(path)!);
  var bytes=WindowsUserProtection.Transform(JsonSerializer.SerializeToUtf8Bytes(receipt),true);
  File.WriteAllBytes(path+".tmp",bytes);File.Move(path+".tmp",path,true);
 }
 public IReadOnlyList<OfferReceipt> Read(Guid owner)
 {
  var dir=Path.GetDirectoryName(PathFor(owner,Guid.Empty))!;if(!Directory.Exists(dir))return [];
  var result=new List<OfferReceipt>();
  foreach(var file in Directory.EnumerateFiles(dir,"*.dat").Take(100))
   try { if(new FileInfo(file).Length>4096)continue;var r=JsonSerializer.Deserialize<OfferReceipt>(WindowsUserProtection.Transform(File.ReadAllBytes(file),false));
    if(r is not null&&r.Owner==owner&&r.Offer!=Guid.Empty&&r.Attempt!=Guid.Empty)result.Add(r);
   }catch{ /* Do not expose another Windows user's or corrupted receipt. */ }
  return result;
 }
 public void Remove(OfferReceipt receipt)=>File.Delete(PathFor(receipt.Owner,receipt.Offer));
}
