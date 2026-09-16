using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace PawLairDiagnostics
{
    internal static class LaunchConfig
    {
        internal const string StockHash="1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45";
        internal static string Hash(string path)
        {using(var input=File.OpenRead(path)) using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(input)).Replace("-","");}
        internal static bool Flag(Dictionary<string,object> settings,string key)
        {object value; return settings.TryGetValue(key,out value) && value is bool && (bool)value;}
        internal static string Text(Dictionary<string,object> settings,string key)
        {object value;return settings.TryGetValue(key,out value) ? Convert.ToString(value) : "";}
        internal static string Select(Dictionary<string,object> s)
        {
            if(Text(s,"mod")!="arcane-wars" || !Flag(s,"pawPatchEnabled") || Flag(s,"dataOnly"))
                throw new InvalidOperationException("Для этой диагностики выбери Arcane Wars с включённым Paw's Patch и примени настройки в лаунчере.");
            bool colors=Flag(s,"customPlayerColors"), hostility=Flag(s,"independentHostility"), sync=Text(s,"desyncMode")=="continue";
            if(colors && !hostility) return sync ? "k2_paws_lobby_colors_mp_nohostility_sync_1372.exe" : "k2_paws_lobby_colors_mp_nohostility_1372.exe";
            if(colors) return sync ? "k2_paws_lobby_colors_mp_sync_1372.exe" : "k2_paws_lobby_colors_mp_1372_experimental.exe";
            if(hostility) return sync ? "k2_paws_sync_family_herd_relations_1372.exe" : "k2_paws_family_herd_relations_1372.exe";
            return sync ? "k2_paws_sync_continue_1372.exe" : "k2_paws_ui_1372.exe";
        }
    }

    internal sealed class SessionLog : IDisposable
    {
        internal readonly string DirectoryPath;
        private StreamWriter writer;
        private int part;
        private readonly object gate=new object();
        private readonly JavaScriptSerializer json=new JavaScriptSerializer { MaxJsonLength=32*1024*1024,RecursionLimit=64 };
        internal SessionLog(string game)
        {
            DirectoryPath=Path.Combine(game,"Logs","PawsLairDiagnostics",DateTime.Now.ToString("yyyyMMdd-HHmmss")+"-"+Process.GetCurrentProcess().Id);
            Directory.CreateDirectory(DirectoryPath); Next();
        }
        private void Next()
        {
            if(writer!=null) writer.Dispose();
            writer=new StreamWriter(Path.Combine(DirectoryPath,"lairs-"+(++part).ToString("000")+".jsonl"),false,new UTF8Encoding(false));
            writer.AutoFlush=true;
        }
        internal void Event(string type,object data)
        {
            lock(gate)
            {
                if(writer==null) return;
                if(writer.BaseStream.Position>32*1024*1024) Next();
                writer.WriteLine(json.Serialize(new {utc=DateTime.UtcNow.ToString("o"),type=type,data=data}));
            }
        }
        internal string Pack()
        {
            lock(gate) {if(writer!=null){writer.Dispose();writer=null;}}
            string zip=DirectoryPath+".zip";ZipFile.CreateFromDirectory(DirectoryPath,zip,CompressionLevel.Optimal,false);return zip;
        }
        public void Dispose() {lock(gate){if(writer!=null)writer.Dispose();writer=null;}}
    }

    internal sealed class DiagnosticForm : Form
    {
        private readonly Label status=new Label();
        private readonly Button mark=new Button();
        private readonly Button folder=new Button();
        private readonly string gamePath;
        private readonly bool attachOnly;
        private volatile bool stop;
        private SessionLog log;
        private string resultPath;
        private volatile bool finished;
        private bool closeAfterFinish;
        internal DiagnosticForm(string game,bool attach)
        {
            gamePath=game;attachOnly=attach;
            Text="Paw's Patch — диагностика логов драконов";
            StartPosition=FormStartPosition.CenterScreen;ClientSize=new Size(640,236);
            Font=new Font("Segoe UI",10);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;
            var help=new Label {Text="Загрузи нужное сохранение или начни матч.\nАтакуй логово, отойди, дождись возвращения защитников и подойди снова.\nПосле воспроизведения выйди из игры — отчёт сохранится автоматически.",AutoSize=false,Location=new Point(20,16),Size=new Size(605,80)};
            status.Location=new Point(20,106);status.Size=new Size(605,66);status.Text="Подготовка диагностики…";
            mark.Text="Баг воспроизвёлся";mark.Location=new Point(20,184);mark.Size=new Size(205,34);mark.Enabled=false;
            mark.Click+=(s,e)=>{if(log!=null){log.Event("USER_MARK",new {note="User observed zero defenders / no second sally"});mark.Text="Отметка сохранена";}};
            folder.Text="Папка отчёта";folder.Location=new Point(240,184);folder.Size=new Size(165,34);folder.Enabled=false;
            folder.Click+=(s,e)=>{if(resultPath!=null) Process.Start(new ProcessStartInfo {FileName=Path.GetDirectoryName(resultPath),UseShellExecute=true});};
            Controls.AddRange(new Control[]{help,status,mark,folder});
            Shown+=(s,e)=>Task.Factory.StartNew(Run,TaskCreationOptions.LongRunning);
            FormClosing+=(s,e)=>{if(!finished){stop=true;closeAfterFinish=true;e.Cancel=true;UpdateStatus("Завершаю запись отчёта…",false);}};
        }
        private void UpdateStatus(string text,bool running)
        {
            if(IsDisposed || !IsHandleCreated) return;
            try{BeginInvoke(new Action(()=>{status.Text=text;mark.Enabled=running;folder.Enabled=resultPath!=null;}));}catch(InvalidOperationException){}
        }
        private readonly HashSet<int> reportedCandidates=new HashSet<int>();
        private bool ReadyGame(Process p)
        {
            try
            {
                p.Refresh();if(p.HasExited || p.MainWindowHandle==IntPtr.Zero) return false;
                ProcessModule module=p.MainModule;if(module==null || module.BaseAddress==IntPtr.Zero) return false;
                if(!String.Equals(Path.GetFullPath(module.FileName),Path.Combine(gamePath,"k2.exe"),StringComparison.OrdinalIgnoreCase))return false;
                using(var memory=new ProcessMemory(p.Id))
                {
                    uint image=unchecked((uint)module.BaseAddress.ToInt64());var reader=new LairReader(memory,image);
                    bool verified=reader.VerifyLayout();
                    if(reportedCandidates.Add(p.Id))log.Event("ATTACH_CANDIDATE",new {pid=p.Id,imageBase=image,verified,layout=reader.DescribeLayout()});
                    return verified && !p.HasExited;
                }
            }
            catch(System.ComponentModel.Win32Exception error){if(error.NativeErrorCode==5)throw;return false;}
            catch(InvalidOperationException){return false;}
            catch(NullReferenceException){return false;}
        }
        private void Run()
        {
            string failure=null;
            try
            {
                string exe=Path.Combine(gamePath,"k2.exe");
                if(!File.Exists(exe) || LaunchConfig.Hash(exe)!=LaunchConfig.StockHash)
                    throw new InvalidOperationException("Диагностика рассчитана на установленный Kohan II 1.3.72. Файл игры не совпадает с проверенной версией.");
                var json=new JavaScriptSerializer {MaxJsonLength=32*1024*1024};
                var state=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(gamePath,".pawpatch","state.json")));
                var settings=(Dictionary<string,object>)state["appliedSettings"];
                string helper=Path.Combine(gamePath,LaunchConfig.Select(settings));
                if(!File.Exists(helper)) throw new FileNotFoundException("Не найден установленный файл запуска: "+helper);
                log=new SessionLog(gamePath);resultPath=Path.Combine(log.DirectoryPath,"lairs-001.jsonl");
                log.Event("START",new {build="lair-observer-1372-r2",gamePath=gamePath,gameSha256=LaunchConfig.StockHash,
                    helper=Path.GetFileName(helper),helperSha256=LaunchConfig.Hash(helper),modules=state["modules"],
                    hostility=LaunchConfig.Flag(settings,"independentHostility"),colors=LaunchConfig.Flag(settings,"customPlayerColors"),
                    desync=LaunchConfig.Text(settings,"desyncMode"),sampling="external read-only, non-atomic, 500 ms; no game/save writes"});
                CopyDefinitions();
                var existing=Process.GetProcessesByName("k2");
                bool alreadyRunning=existing.Length!=0;foreach(var process in existing)process.Dispose();
                if(!alreadyRunning && !attachOnly)
                {
                    UpdateStatus("Запускаю установленную игру с твоими текущими настройками…",false);
                    Process.Start(new ProcessStartInfo {FileName=helper,WorkingDirectory=gamePath,UseShellExecute=true});
                }
                var waiting=Stopwatch.StartNew();
                UpdateStatus("Ожидаю готовую игру после запуска через Steam…",false);
                Process game=GameAttachment.Wait(()=>Process.GetProcessesByName("k2"),ReadyGame,p=>p.Dispose(),
                    ()=>stop,()=>waiting.ElapsedMilliseconds,ms=>Thread.Sleep(ms),180000);
                if(stop)return;
                if(game==null) throw new InvalidOperationException("Не обнаружен готовый совместимый процесс игры. Можно запустить игру через обычный лаунчер и затем открыть диагностику.");
                using(game) using(var memory=new ProcessMemory(game.Id))
                {
                    uint image=unchecked((uint)game.MainModule.BaseAddress.ToInt64());
                    var reader=new LairReader(memory,image);
                    if(!reader.VerifyLayout()) throw new InvalidOperationException("Не совпала структура памяти игры. Запись не начата; игра не изменялась.");
                    log.Event("ATTACH",new {pid=game.Id,imageBase=image});
                    Dictionary<uint,string> last=new Dictionary<uint,string>();
                    uint world=0;float? time=null;int frameNo=0;
                    var clock=Stopwatch.StartNew();
                    while(!stop && !game.HasExited)
                    {
                        long started=clock.ElapsedMilliseconds;
                        Frame frame=reader.Capture();
                        if(frame==null)
                        {
                            if(world!=0){log.Event("WORLD_INACTIVE",new {});last.Clear();world=0;}
                            UpdateStatus("Диагностика подключена. Ожидаю загрузки матча…",true);
                        }
                        else
                        {
                            bool baseline=world!=frame.world || frame.gameTime<time || frameNo%20==0;
                            if(world!=frame.world || frame.gameTime<time){last.Clear();log.Event("WORLD",new {frame.world,frame.sessionKind,frame.gameTime});}
                            world=frame.world;time=frame.gameTime;
                            var present=new HashSet<uint>();
                            foreach(var lair in frame.lairs)
                            {
                                present.Add(lair.actor.id);string value=json.Serialize(lair),old;
                                if(baseline || !last.TryGetValue(lair.actor.id,out old) || value!=old)
                                    log.Event("DENIZEN",new {frameNo=frameNo,gameTime=frame.gameTime,world=world,snapshot=lair});
                                last[lair.actor.id]=value;
                            }
                            foreach(uint gone in last.Keys.Where(id=>!present.Contains(id)).ToArray())
                            {log.Event("NOT_OBSERVED",new {actorId=gone,frame.gameTime});last.Remove(gone);}
                            if(baseline || frameNo%2==0) log.Event("FRAME",new {frameNo,frame.world,frame.gameTime,frame.complete,frame.registeredObjects,
                                count=frame.lairs.Count,frame.kingdoms,readMilliseconds=clock.ElapsedMilliseconds-started});
                            int dragons=frame.lairs.Count(l=>l.actor.dataId.IndexOf("dragon",StringComparison.OrdinalIgnoreCase)>=0 || l.actor.dataId.IndexOf("drake",StringComparison.OrdinalIgnoreCase)>=0);
                            UpdateStatus("Запись идёт. Объектов с ополчением: "+frame.lairs.Count+"; логов драконов: "+dragons+".\nКогда увидишь баг, можно нажать «Баг воспроизвёлся» или просто выйти из игры.",true);
                            frameNo++;
                        }
                        int pause=500-(int)(clock.ElapsedMilliseconds-started);if(pause>0)Thread.Sleep(pause);
                    }
                    log.Event("STOP",new {reason=stop ? "observer closed" : "game exited",frames=frameNo});
                }
            }
            catch(Exception error)
            {
                failure=error.Message;
                if(log!=null) log.Event("ERROR",new {message=error.ToString()});
                UpdateStatus(error.Message,false);
                if(!stop && !IsDisposed) try{BeginInvoke(new Action(()=>MessageBox.Show(this,error.Message,"Диагностика логов",MessageBoxButtons.OK,MessageBoxIcon.Information)));}catch(InvalidOperationException){}
            }
            finally
            {
                if(log!=null)
                {
                    try{resultPath=log.Pack();UpdateStatus(failure ?? "Запись закончена. Архив отчёта сохранён.\nМожно закрыть это окно и написать, удалось ли воспроизвести баг.",false);}
                    catch(Exception error){log.Dispose();UpdateStatus("Логи сохранены, архив не создан: "+error.Message,false);}
                }
                finished=true;
                if(closeAfterFinish && !IsDisposed) try{BeginInvoke(new Action(Close));}catch(InvalidOperationException){}
            }
        }
        private void CopyDefinitions()
        {
            // Exact installed data, including local overrides; no profile/settings file is copied.
            string root=Path.Combine(gamePath,"Data");
            foreach(string relative in new[]{"Buildings\\LairsMonster\\AW_dragon_lair.tgi","Buildings\\LairsMonster\\AW_storm_drake_crag.tgi",
                "Units\\Monster\\AW_dragon_fire.tgi","Units\\Monster\\AW_young_dragon_fire.tgi","Units\\Monster\\AW_youngling_dragon_fire.tgi",
                "Units\\Monster\\AW_storm_drake.tgi","Units\\Monster\\AW_young_storm_drake.tgi","Units\\Monster\\AW_youngling_storm_drake.tgi",
                "Templates\\template_rmc_k2.tgi","Game\\SVars.tgi"})
            {
                string src=Path.Combine(root,relative);if(!File.Exists(src))continue;
                string dst=Path.Combine(log.DirectoryPath,"definitions",relative);Directory.CreateDirectory(Path.GetDirectoryName(dst));File.Copy(src,dst);
                log.Event("DEFINITION",new {path=relative,sha256=LaunchConfig.Hash(src)});
            }
        }
    }

    internal static class Program
    {
        [STAThread] private static void Main(string[] args)
        {
            Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
            string path=@"D:\SteamLibrary\steamapps\common\Kohan II";
            for(int i=0;i+1<args.Length;i++) if(args[i]=="--game")path=Path.GetFullPath(args[i+1]);
            using(var mutex=new Mutex(false,"Local\\PawsLairDiagnostics1372"))
            {
                if(!mutex.WaitOne(0)){MessageBox.Show("Диагностика уже запущена.");return;}
                try{Application.Run(new DiagnosticForm(path,args.Contains("--attach")));}
                finally{mutex.ReleaseMutex();}
            }
        }
    }
}
