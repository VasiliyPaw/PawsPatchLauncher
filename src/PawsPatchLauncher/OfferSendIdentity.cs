using System.Security.Cryptography;
using System.Text;
namespace PawsPatchLauncher;
public static class OfferSendIdentity
{
 public static string Key(Guid owner,Guid peer,string payload)=>Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(owner+"|"+peer+"|"+payload)));
 public static Guid Get(string root,string key)
 {
  var file=Path.Combine(root,"account","offer-sends",key+".dat");Directory.CreateDirectory(Path.GetDirectoryName(file)!);
  if(File.Exists(file))try { return new Guid(WindowsUserProtection.Transform(File.ReadAllBytes(file),false)); }catch{}
  var id=Guid.NewGuid();File.WriteAllBytes(file+".tmp",WindowsUserProtection.Transform(id.ToByteArray(),true));File.Move(file+".tmp",file,true);return id;
 }
 public static void Complete(string root,string key)=>File.Delete(Path.Combine(root,"account","offer-sends",key+".dat"));
}
