using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Globalization;
using System.Collections.Generic;
using System.Web.Script.Serialization;

internal static class AiPolicyRuntime
{
    static uint cave,image,last; static int pid; static DateTime next;
    static NativeMemory reader; static string folder; static StreamWriter writer;
    static long bytes; static int part; static uint dropped;
    static AiDiagnosticsSnapshot snapshot; static DateTime nextSnapshot; static StreamWriter snapshots; static int snapshotPart,snapshotCount;
    static StreamWriter important,timeline; static int importantPart,timelinePart;
    static readonly JavaScriptSerializer json=new JavaScriptSerializer {MaxJsonLength=16*1024*1024,RecursionLimit=64};
    internal static void Validate(IMemory m,uint b) {
        for(int i=0;i<AiPolicyPayload.Sites.Length;i++)TerrainPatch.Expect(m,b+AiPolicyPayload.Sites[i]-3,TerrainPatch.Hex(AiPolicyPayload.Guards[i]));
    }
    internal static void Install(IMemory m,uint b,int processId,string gameDir,Action<string> log) {
        uint mem=InstallNative(m,b,log);
        cave=mem;image=b;pid=processId;last=0;next=DateTime.MinValue;
        // File-system failure must not roll back valid gameplay fixes or prevent play.
        try {
            folder=Path.Combine(gameDir,"paws_ai_diagnostics",DateTime.Now.ToString("yyyyMMdd-HHmmss")+"-"+pid);
            Directory.CreateDirectory(folder);
            File.WriteAllText(Path.Combine(folder,"session.json"),json.Serialize(new { revision=5,pid=pid,image=image,cave=cave,mode="allied-expansion-recruit-limits-city-lifecycle",policyMask=7,maxMegabytes=56,decisions="rolling 4 x 4 MiB",snapshots="rolling 4 x 4 MiB; every 10 wall seconds; asynchronous",counterMeaning="0-10 all evaluations; 20 allied site veto; 21-24 old duplicate sampling; 25-26 bulk sampling; 27 new duplicate sampling; 28 early capacity veto; 29 stale center veto; dropped is transport loss",timeline="2 x 4 MiB economic summaries; 2 x 4 MiB recruitment and vetoes",kind0="goal priority aggregated by kingdom/type/state/eligibility, max 64 per game second; result is goal vtable RVA; stateOrCityId is goal state",kind1="recruit preparation; result 1=city selected, 0=no selected city; stateOrCityId is selected city actor ID",kind2="construction candidate; before/after score; counter20 counts allied site vetoes",kind3="native recruitment requirements; result 0=eligible, nonzero=native rejection code, not necessarily lack of gold; stateOrCityId is city actor ID",kind4="early recruit eligibility; result 0=pass, uint.MaxValue=native template rejection, otherwise limited resource index+1; before=requested, after=remaining, stateOrCityId=used, finalPriority=capacity (only capacity failures)",kind5="final planning capacity check using actual layout and reserved budgets; result 0=pass, resource index+1=blocked, 4294967294=unclassified native refusal; same capacity fields as kind4",kind6="native recruit queue insertion executed; city ID; not a completed company",kind7="native queued/direct recruit validation; result 1=pass, 0=fail; city ID",kind8="native capacity admission; result 0=pass, otherwise native blocked resource index+1; city ID",kind9="child-building precondition; result 0=forwarded to native validation, 1=invalid settlement, 2=missing/removed center, 3=owner mismatch, 4=dead/invalid body; city and center IDs; original siege validation preserved",kind10="direct AI company creation result: 1=created, 0=failed; no recruitment queue used; city ID",gameExeSha256=Hash(Path.Combine(gameDir,"k2.exe")) }));
            File.WriteAllText(Path.Combine(folder,"README.txt"),"Автоматическая локальная диагностика ботов. Отправки в интернет нет.\r\nРешения записываются при их принятии. Снимки городов и рот — раз в 10 секунд реального времени; они асинхронные, сравнивайте gameTimeStart/gameTimeEnd.\r\nПовтор одинаковых решений записывается не чаще раза в 5 игровых секунд. Счётчики учитывают все проверки; dropped показывает потерянные записи.\r\nХранятся четыре сменяемых файла решений и четыре файла снимков, до 4 МиБ каждый. Первый снимок сохраняется отдельно. До 56 МиБ на запуск; старые запуски автоматически не удаляются.\r\nkind=3: результат штатной проверки требований найма. 0 означает допустимость этой проверки, а не гарантированный найм. Ненулевой код сам по себе не доказывает недостаток золота.\r\nkind=4/5: вместимость при выборе состава и окончательной подготовке; код ресурса — индекс + 1. kind=6: вызов постановки в очередь, а не завершённый найм. kind=7/8: окончательные проверки перед постановкой. kind=9: строительство при действующем центре; ненулевой результат — причина отказа.\r\nМеста расширения, уже занятые активным строителем союзника, исключаются из повторного выбора. Ремонт не изменён.\r\n");
            AppDomain.CurrentDomain.ProcessExit+=delegate {Stop();};
            log("AI_POLICY r5; early limited-capacity eligibility; final admission/queue diagnostics; stale center build guard; cave=0x"+mem.ToString("X8")+" reports="+folder);
        } catch(Exception e) { cave=0;log("AI_DIAGNOSTICS_DISABLED: "+e.Message); }
    }
    internal static uint InstallNative(IMemory m,uint b,Action<string> log) {
        Validate(m,b);uint mem=0;int attempted=-1;bool free=true;
        try {
            mem=m.Allocate(AiPolicyPayload.Allocation);var code=AiPolicyPayload.Build(b,mem);
            m.Write(mem,code);TerrainPatch.Expect(m,mem,code);
            var initial=new byte[AiPolicyPayload.Allocation-AiPolicyPayload.DataOffset];
            Buffer.BlockCopy(BitConverter.GetBytes(7u),0,initial,4,4);
            Buffer.BlockCopy(BitConverter.GetBytes(mem+(uint)AiPolicyPayload.QueryOffset),0,initial,AiPolicyPayload.QueryPointerOffset,4);
            m.Write(mem+(uint)AiPolicyPayload.DataOffset,initial);
            m.MakeExecutable(mem,AiPolicyPayload.CodeSize);m.Flush(mem,code.Length);
            for(int i=0;i<AiPolicyPayload.Sites.Length;i++) {
                attempted=i;free=false;var call=TerrainPatch.Call(b+AiPolicyPayload.Sites[i],mem+AiPolicyPayload.Offsets[i]);
                m.WriteCode(b+AiPolicyPayload.Sites[i],call);TerrainPatch.Expect(m,b+AiPolicyPayload.Sites[i],call);m.Flush(b+AiPolicyPayload.Sites[i],5);
            }
            return mem;
        } catch {
            free=true;
            for(int i=attempted;i>=0;i--)try {var original=TerrainPatch.Hex(AiPolicyPayload.Originals[i]);m.WriteCode(b+AiPolicyPayload.Sites[i],original);TerrainPatch.Expect(m,b+AiPolicyPayload.Sites[i],original);m.Flush(b+AiPolicyPayload.Sites[i],5);}catch(Exception e){free=false;log("AI_POLICY_ROLLBACK_UNCERTAIN: "+e.Message);}
            if(mem!=0&&free)m.Free(mem);throw;
        }
    }
    static uint U(byte[] b,int o){return BitConverter.ToUInt32(b,o);}
    static string Hash(string path){using(var sha=System.Security.Cryptography.SHA256.Create())using(var file=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(file)).Replace("-","").ToLowerInvariant();}
    static object F(byte[] b,int o){float f=BitConverter.ToSingle(b,o);return float.IsNaN(f)||float.IsInfinity(f)?(object)null:(object)f;}
    static void Rolling(ref StreamWriter stream,ref int partNumber,string prefix,string line){
        if(stream==null||stream.BaseStream.Length+Encoding.UTF8.GetByteCount(line)+2>4*1024*1024){if(stream!=null)stream.Dispose();stream=new StreamWriter(Path.Combine(folder,prefix+"-"+((partNumber++%2)+1)+".jsonl"),false,new UTF8Encoding(false));}
        stream.WriteLine(line);stream.Flush();
    }
    static void Stop(){try{if(writer!=null)writer.Dispose();if(snapshots!=null)snapshots.Dispose();if(important!=null)important.Dispose();if(timeline!=null)timeline.Dispose();if(reader!=null)reader.Dispose();if(folder!=null)File.WriteAllText(Path.Combine(folder,"closed.json"),json.Serialize(new {closedUtc=DateTime.UtcNow,lastSequence=last,dropped=dropped,totalBytesWritten=bytes,snapshots=snapshotCount}));}catch{}}
    internal static void Tick() {
        if(cave==0||DateTime.UtcNow<next)return;next=DateTime.UtcNow.AddMilliseconds(500);
        try {
            if(reader==null){reader=new NativeMemory(pid);snapshot=new AiDiagnosticsSnapshot(reader,image);}
            uint data=cave+(uint)AiPolicyPayload.DataOffset;var head=reader.Read(data,128);uint seq=U(head,0);
            if(seq-last>2048){dropped+=seq-last-2048;last=seq-2048;}
            if(seq!=last) {
                var ring=reader.Read(data+128,2048*128);
                uint available=unchecked(seq-last);
                for(uint index=1;index<=available;index++) {
                    uint n=unchecked(last+index);
                    int o=(int)((n-1)&2047)*128;if(U(ring,o)!=n||U(ring,o+124)!=n){dropped++;continue;}
                    if(writer==null || writer.BaseStream.Length>=4*1024*1024) {
                        if(writer!=null)writer.Dispose();writer=new StreamWriter(Path.Combine(folder,"decisions-"+((part++%4)+1)+".jsonl"),false,new UTF8Encoding(false));
                    }
                    string name=Encoding.ASCII.GetString(ring,o+64,60).Split('\0')[0];
                    var line=json.Serialize(new { seq=n,world=U(ring,o+4),time=F(ring,o+8),kind=U(ring,o+12),kingdom=U(ring,o+16),objectAddress=U(ring,o+20),definition=name,result=U(ring,o+28),before=F(ring,o+32),after=F(ring,o+36),gold=F(ring,o+40),income=F(ring,o+44),stateOrCityId=F(ring,o+48),finalPriority=F(ring,o+52),x=F(ring,o+56),y=F(ring,o+60) });
                    writer.WriteLine(line);bytes+=Encoding.UTF8.GetByteCount(line)+1;
                    uint kind=U(ring,o+12);if(kind==1||kind>=3||(kind==2&&U(ring,o+32)!=U(ring,o+36)))Rolling(ref important,ref importantPart,"recruitment-and-vetoes",line);
                }
                if(writer!=null)writer.Flush();
            }
            last=seq;var counts=new uint[30];for(int i=0;i<30;i++)counts[i]=U(head,8+i*4);
            File.WriteAllText(Path.Combine(folder,"status.json"),json.Serialize(new { sequence=seq,dropped=dropped,totalBytesWritten=bytes,rollingParts=part,snapshots=snapshotCount,counts=counts }));
            if(DateTime.UtcNow>=nextSnapshot){nextSnapshot=DateTime.UtcNow.AddSeconds(10);try{
                var watch=Stopwatch.StartNew();object state=snapshot.Capture();if(state!=null){var line=json.Serialize(new {wallUtc=DateTime.UtcNow,captureMilliseconds=watch.ElapsedMilliseconds,state=state});
                    if(Encoding.UTF8.GetByteCount(line)>4*1024*1024)throw new InvalidOperationException("Snapshot exceeds report limit");
                    if(snapshots==null||snapshots.BaseStream.Length+Encoding.UTF8.GetByteCount(line)>4*1024*1024){if(snapshots!=null)snapshots.Dispose();snapshots=new StreamWriter(Path.Combine(folder,"snapshots-"+((snapshotPart++%4)+1)+".jsonl"),false,new UTF8Encoding(false));}
                    snapshots.WriteLine(line);snapshots.Flush();if(snapshotCount++==0)File.WriteAllText(Path.Combine(folder,"first-snapshot.json"),line);
                    Rolling(ref timeline,ref timelinePart,"economy-timeline",json.Serialize(new {wallUtc=DateTime.UtcNow,state=snapshot.Summary}));
                }
            }catch(Exception e){File.WriteAllText(Path.Combine(folder,"snapshot-error.txt"),DateTime.UtcNow.ToString("o")+" "+e.Message);}}
        } catch(Exception e) {
            // Diagnostics cannot stop the running game.
            if(folder!=null)try{File.WriteAllText(Path.Combine(folder,"diagnostics-error.txt"),e.Message);}catch{}
            next=DateTime.UtcNow.AddSeconds(10);
        }
    }
}
