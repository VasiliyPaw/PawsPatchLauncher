using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Web.Script.Serialization;

namespace PawLairDiagnostics
{
    // Explicit PID, read-only attach, no launch/injection/window/input control.
    internal static class LiveCapture
    {
        private static int Main(string[] args)
        {
            if(args.Length!=2)return 2;
            int pid;if(!Int32.TryParse(args[0],out pid))return 2;
            string gameRoot=Path.GetFullPath(args[1]);SessionLog log=null;
            try
            {
                using(var game=Process.GetProcessById(pid))
                {
                    string gameExe=Path.Combine(gameRoot,"k2.exe");
                    if(!String.Equals(game.MainModule.FileName,gameExe,StringComparison.OrdinalIgnoreCase)
                        || LaunchConfig.Hash(gameExe)!=LaunchConfig.StockHash)throw new InvalidOperationException("Wrong game path or image hash.");
                    using(var memory=new ProcessMemory(pid))
                    {
                        uint image=unchecked((uint)game.MainModule.BaseAddress.ToInt64());
                        var reader=new LairReader(memory,image);
                        if(!reader.VerifyLayout())throw new InvalidOperationException("Live layout not verified.");
                        log=new SessionLog(gameRoot);
                        var state=new JavaScriptSerializer{MaxJsonLength=32*1024*1024}.DeserializeObject(File.ReadAllText(Path.Combine(gameRoot,".pawpatch","state.json"))) as System.Collections.Generic.Dictionary<string,object>;
                        log.Event("START",new {build="lair-live-readonly-r2",pid,imageBase=image,modules=state["modules"],sampling="500 ms dragon snapshots; all Denizen components every 10 seconds; external non-atomic reads"});
                        log.Event("ATTACH",new {pid,imageBase=image,layout=reader.DescribeLayout()});
                        File.WriteAllText(Path.Combine(log.DirectoryPath,"capture-status.json"),"{\"attached\":true,\"pid\":"+pid+"}");
                        int samples=0;var watch=Stopwatch.StartNew();var json=new JavaScriptSerializer{MaxJsonLength=32*1024*1024};
                        while(!game.HasExited && watch.Elapsed.TotalHours<4 && !File.Exists(Path.Combine(log.DirectoryPath,"stop.request")))
                        {
                            long begin=watch.ElapsedMilliseconds;Frame frame=reader.Capture();
                            if(frame!=null)
                            {
                                var dragons=frame.lairs.Where(l=>l.actor.dataId.IndexOf("dragon",StringComparison.OrdinalIgnoreCase)>=0 || l.actor.dataId.IndexOf("drake",StringComparison.OrdinalIgnoreCase)>=0).ToArray();
                                log.Event("LIVE_FRAME",new {samples,frame.world,frame.gameTime,frame.complete,frame.registeredObjects,frame.kingdoms,
                                    lairs=samples%20==0?frame.lairs.ToArray():dragons,readMilliseconds=watch.ElapsedMilliseconds-begin});
                                File.WriteAllText(Path.Combine(log.DirectoryPath,"capture-status.json"),json.Serialize(new {pid,samples,frame.gameTime,components=frame.lairs.Count,dragons=dragons.Length,frame.complete,readMilliseconds=watch.ElapsedMilliseconds-begin,utc=DateTime.UtcNow.ToString("o")}));
                            }
                            else if(samples%10==0)log.Event("WAIT_WORLD",new {pid,samples});
                            samples++;int pause=500-(int)(watch.ElapsedMilliseconds-begin);if(pause>0)Thread.Sleep(pause);
                        }
                        log.Event("STOP",new {samples,reason=game.HasExited?"game exited":"requested or time limit"});
                    }
                }
                return 0;
            }
            catch(Exception error){if(log!=null)log.Event("ERROR",new {message=error.ToString()});Console.Error.WriteLine(error);return 1;}
            finally{if(log!=null){try{log.Pack();}finally{log.Dispose();}}}
        }
    }
}
