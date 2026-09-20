using System;
using System.Collections.Generic;
using System.Text;
using System.Web.Script.Serialization;
interface IMemory {byte[] Read(uint p,int n);}
sealed class Fixture:IMemory {
 internal readonly Dictionary<uint,byte> bytes=new Dictionary<uint,byte>();
 internal Action<uint,int> OnRead; internal int Reads;
 internal void Put(uint p,byte[] b){for(int i=0;i<b.Length;i++)bytes[p+(uint)i]=b[i];}
 internal void Zero(uint p,int n){Put(p,new byte[n]);}
 internal void U(uint p,uint value){Put(p,BitConverter.GetBytes(value));}
 internal void F(uint p,float value){Put(p,BitConverter.GetBytes(value));}
 internal void Text(uint p,string text){Zero(p,256);Put(p,Encoding.Unicode.GetBytes(text+"\0"));}
 public byte[] Read(uint p,int n){Reads++;if(OnRead!=null)OnRead(p,n);var b=new byte[n];for(int i=0;i<n;i++)if(!bytes.TryGetValue(p+(uint)i,out b[i]))throw new InvalidOperationException("Unmapped "+(p+i).ToString("X"));return b;}
}
class SnapshotTests {
 const uint B=0x460000,W=0x100000,K=0x110000,P=0x120000,E=0x130000,S=0x140000,T=0x150000,R=0x160000,A=0x210000;
 static int checks;
 static void Check(bool value){checks++;if(!value)throw new Exception("Check "+checks);}
 static Fixture Make(){var m=new Fixture();m.Zero(B,0x690000);foreach(uint p in new[]{W,K,P,E,S,T,A})m.Zero(p,0x1000);m.Zero(R,0x60004);
  m.U(B+0x5f3fb8,W);m.U(B+0x5f9218,2);m.U(B+0x5f3fb4,T);m.U(B+0x5f3fc8,S);m.U(B+0x5ef72c,R);m.F(W+0xe8,42);
  m.U(W+0x150,W+0x200);m.U(W+0x154,1);m.U(W+0x200,K);
  m.U(T+0x34,T+0x100);m.U(T+0x38,2);for(uint i=0;i<2;i++){uint def=T+0x300+i*0x200;m.U(T+0x100+i*4,def);m.U(def+8,def+0x80);m.Text(def+0x80,i==0?"gold":"unit_limit_provided");}
  m.U(S+0x6c,S+0x100);m.U(S+0x70,1);m.U(S+0x100,P);m.U(P+8,K);m.U(P+0xc,E);m.U(E+4,P);
  m.U(K+0x1a0,K+0x300);m.Text(K+0x300,"София");m.U(K+0x1a8,K+0x500);m.U(K+0x1c0,K+0x510);m.U(K+0x1cc,K+0x520);m.U(K+0x1d0,2);m.F(K+0x500,150);m.F(K+0x510,50);m.F(K+0x520,1000);
  m.U(K+0x2dc,K+0x600);m.U(K+0x2e0,1);m.U(K+0x600,A);m.U(A+0x14,123);m.U(A+0xe8,K);m.F(A+0x20,100);m.F(A+0x24,200);
  return m;
 }
 static int Main(){var json=new JavaScriptSerializer {MaxJsonLength=4000000};var m=Make();var reader=new AiDiagnosticsSnapshot(m,B);string text=json.Serialize(reader.Capture());
  Check(text.Contains("София"));Check(text.Contains("\"gameTimeStart\":42"));Check(text.Contains("\"stock\":[1000,0]"));Check(text.Contains("\"id\":123"));Check(text.Contains("\"asynchronous\":true"));
  m.U(B+0x5f9218,1);Check(reader.Capture()==null);m.U(B+0x5f9218,2);
  m.F(K+0x500,float.NaN);Check(json.Serialize(reader.Capture()).Contains("\"production\":[null,0]"));
  int visits=0;m.OnRead=delegate(uint p,int n){if(p==B+0x5f3fb8&&++visits==2)m.U(p,W+0x1000);};Check(reader.Capture()==null);m.OnRead=null;m.U(B+0x5f3fb8,W);
  m.U(K+0x2e0,1000000);bool denied=false;try{reader.Capture();}catch(InvalidOperationException){denied=true;}Check(denied);
  m=Make();reader=new AiDiagnosticsSnapshot(m,B);m.U(P+0x2c,P+0x100);m.U(P+0x100,P+0x200);m.U(P+0x104,P+0x100);m.U(P+0x208,123);m.U(P+0x20c,P);m.U(R+0x20004+123*4,A);text=json.Serialize(reader.Capture());Check(text.Contains("\"actor\":{\"id\":123"));Check(m.Reads<100);
  m.U(A+0x14,124);text=json.Serialize(reader.Capture());Check(text.Contains("\"actor\":null"));
  Console.WriteLine("AI_SNAPSHOT_PASS "+checks+" checks; read-only fixtures; loading, NaN, world changes, cycles, limits, stale actor IDs");return 0;
 }
}
