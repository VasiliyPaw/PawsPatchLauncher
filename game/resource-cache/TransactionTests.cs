using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
internal static class CacheTransactionTests
{
 sealed class Memory:IMemory {
  readonly Dictionary<uint,byte> bytes=new Dictionary<uint,byte>();
  readonly byte[] allocated=new byte[ResourceCachePayload.Allocation];
  internal int Operations,FailAt=-1;internal bool Allocated,PersistentFailure;
  internal void Seed(uint a,byte[] b){for(int i=0;i<b.Length;i++){uint p=a+(uint)i;if(p>=0x60000000&&p<0x60000000+allocated.Length)allocated[p-0x60000000]=b[i];else bytes[p]=b[i];}}
  void Op(){if(++Operations==FailAt)throw new IOException("injected failure");}
  internal Memory(uint image){for(int i=0;i<ResourceCachePayload.Sites.Length;i++)Seed(image+ResourceCachePayload.Sites[i],ResourceCachePayload.Original(i,image));}
  public byte[] Read(uint a,int n){Op();var result=new byte[n];for(int i=0;i<n;i++){uint p=a+(uint)i;if(p>=0x60000000&&p<0x60000000+allocated.Length)result[i]=allocated[p-0x60000000];else bytes.TryGetValue(p,out result[i]);}return result;}
  public void Write(uint a,byte[] b){Seed(a,b.Take(2).ToArray());Op();Seed(a,b);}
  public void WriteCode(uint a,byte[] b){Seed(a,b.Take(2).ToArray());Op();if(PersistentFailure)throw new IOException("persistent partial write");Seed(a,b);}
  public uint Allocate(int n){Op();if(n!=ResourceCachePayload.Allocation)throw new Exception("allocation");Allocated=true;return 0x60000000;}
  public void MakeExecutable(uint a,int n){Op();if(n!=ResourceCachePayload.CodeSize)throw new Exception("writable data must be separate");}
  public void Flush(uint a,int n){Op();}
  public void Free(uint a){Allocated=false;}
 }
 static int checks;static void Check(bool yes){checks++;if(!yes)throw new Exception("Cache transaction check "+checks);}
 internal static int Main(){using(var self=Process.GetCurrentProcess())foreach(uint image in new uint[]{0x460000,0xf20000,0x18000000}){
  var success=new Memory(image);ResourceCachePatch.Install(self,success,image,delegate{});int operations=success.Operations;
  Check(success.Allocated);Check(BitConverter.ToUInt32(success.Read(0x60000000+ResourceCachePayload.State,4),0)==image);
  Check(BitConverter.ToUInt32(success.Read(0x60000000+ResourceCachePayload.State+12,4),0)==1);
  for(int i=0;i<2;i++){uint site=image+ResourceCachePayload.Sites[i];var b=success.Read(site,ResourceCachePayload.Original(i,image).Length);Check(b[0]==0xe9);Check(unchecked(site+5+BitConverter.ToUInt32(b,1))==0x60000000+ResourceCachePayload.Entries[i]);}
  for(int fault=1;fault<=operations;fault++){
   var m=new Memory(image){FailAt=fault};bool threw=false;try{ResourceCachePatch.Install(self,m,image,delegate{});}catch(IOException){threw=true;}
   Check(threw&&!m.Allocated);for(int i=0;i<2;i++)Check(m.Read(image+ResourceCachePayload.Sites[i],ResourceCachePayload.Original(i,image).Length).SequenceEqual(ResourceCachePayload.Original(i,image)));
  }
  foreach(uint site in ResourceCachePayload.Sites){var m=new Memory(image);m.Seed(image+site,new byte[]{0xcc});bool rejected=false;try{ResourceCachePatch.Install(self,m,image,delegate{});}catch(InvalidOperationException){rejected=true;}Check(rejected&&!m.Allocated);}
  var persistent=new Memory(image){PersistentFailure=true};try{ResourceCachePatch.Install(self,persistent,image,delegate{});}catch(IOException){}Check(persistent.Allocated);
 }
 Console.WriteLine("RESOURCE_CACHE_TRANSACTION_PASS "+checks+" checks; ASLR, preflight, partial writes, rollback, uncertain rollback retention");return 0;}
}
