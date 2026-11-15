using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

// Owns only the process it starts in sandbox/. Never attaches to an existing game.
sealed class Probe : Form
{
    [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint a,bool b,int c);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool ReadProcessMemory(IntPtr h,IntPtr p,byte[] b,int n,out IntPtr used);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool WriteProcessMemory(IntPtr h,IntPtr p,byte[] b,int n,out IntPtr used);
    [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr VirtualAllocEx(IntPtr h,IntPtr p,uint n,uint a,uint protect);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool VirtualProtectEx(IntPtr h,IntPtr p,uint n,uint protect,out uint old);
    [DllImport("kernel32.dll")] static extern bool FlushInstructionCache(IntPtr h,IntPtr p,uint n);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
    [DllImport("ntdll.dll")] static extern int NtSuspendProcess(IntPtr h);
    [DllImport("ntdll.dll")] static extern int NtResumeProcess(IntPtr h);

    readonly string root=AppDomain.CurrentDomain.BaseDirectory;
    readonly Label status=new Label { AutoSize=false,Height=74,Dock=DockStyle.Top };
    readonly Button launch=new Button { Text="Запустить отдельную тестовую игру",AutoSize=true };
    readonly FlowLayoutPanel actions=new FlowLayoutPanel { AutoSize=true,Dock=DockStyle.Top };
    readonly PictureBox mapView=new PictureBox { Dock=DockStyle.Fill,BackColor=Color.FromArgb(15,25,35),SizeMode=PictureBoxSizeMode.StretchImage };
    readonly NumericUpDown x=new NumericUpDown(),y=new NumericUpDown(),width=new NumericUpDown(),height=new NumericUpDown();
    readonly Timer timer=new Timer { Interval=500 };
    Process game;IntPtr handle;uint image,cave,state;bool busy,attaching;uint[] last;int serial,lastLogged=-1;
    static uint N(object v) { return Convert.ToUInt32(v); }
    static IntPtr P(uint p) { return new IntPtr(unchecked((int)p)); }
    byte[] Read(uint at,int length) { var b=new byte[length];IntPtr n;if(!ReadProcessMemory(handle,P(at),b,length,out n)||n.ToInt32()!=length)throw new IOException("Не удалось прочитать состояние тестовой игры.");return b; }
    uint U(uint at) { return BitConverter.ToUInt32(Read(at,4),0); }
    void Write(uint at,byte[] b) { IntPtr n;if(!WriteProcessMemory(handle,P(at),b,b.Length,out n)||n.ToInt32()!=b.Length)throw new IOException("Не удалось записать команду теста."); }
    void W(uint at,uint v) { Write(at,BitConverter.GetBytes(v)); }
    void Log(string text) { File.AppendAllText(Path.Combine(root,"probe.log"),DateTime.Now.ToString("O")+" "+text+Environment.NewLine); }

    [STAThread] static void Main() { Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new Probe()); }
    Probe()
    {
        Text="Paw's Terrain — локальный прототип";ClientSize=new Size(520,640);MinimumSize=new Size(500,550);Font=new Font("Segoe UI",10);
        var top=new FlowLayoutPanel { Dock=DockStyle.Top,AutoSize=true };top.Controls.Add(launch);
        var fields=new FlowLayoutPanel { Dock=DockStyle.Top,AutoSize=true };
        var nums=new[]{x,y,width,height};var names=new[]{"X","Y","Ширина","Высота"};
        for(int i=0;i<4;i++){nums[i].Width=58;nums[i].Maximum=i>1?128:127;nums[i].Minimum=i>1?1:0;nums[i].Value=i>1?4:8;fields.Controls.Add(new Label { Text=names[i],AutoSize=true,Margin=new Padding(3,7,0,0) });fields.Controls.Add(nums[i]);}
        string[] labels={"Суша / проход","Вода","Дорога: +20% к базе"};
        for(uint k=0;k<3;k++){uint kind=k;var b=new Button { Text=labels[k],AutoSize=true };b.Click+=(s,e)=>PaintTerrain(kind);actions.Controls.Add(b);}
        var help=new Label { Dock=DockStyle.Bottom,Height=92,Text="В игре: загрузите Crossing-open или Crossing-closed.\nВыберите участок на схеме и покрытие, затем вернитесь в окно игры: смена окон ставит игру на паузу.\nПосле открытия прохода выдайте роте новый приказ." };
        Controls.Add(mapView);Controls.Add(help);Controls.Add(actions);Controls.Add(fields);Controls.Add(status);Controls.Add(top);
        status.Text="Подготовлено для проверки. Настоящая установка игры и её сохранения не используются.";actions.Enabled=false;
        launch.Click+=async(s,e)=>await Launch();timer.Tick+=(s,e)=>Poll();
        mapView.MouseClick+=(s,e)=>{if(last==null||last[13]==0||last[14]==0)return;x.Value=Math.Min(127,e.X*last[13]/Math.Max(1,mapView.Width));y.Value=Math.Min(127,e.Y*last[14]/Math.Max(1,mapView.Height));};
        FormClosed+=(s,e)=>{timer.Stop();if(handle!=IntPtr.Zero)CloseHandle(handle);};
        FormClosing+=(s,e)=>{if(attaching){e.Cancel=true;status.Text="Подключение теста завершается. Подождите несколько секунд.";}};
    }
    async Task Launch()
    {
        if(game!=null&&!game.HasExited)return;launch.Enabled=false;attaching=true;status.Text="Запускается отдельная копия игры…";
        try
        {
            string exe=Path.Combine(root,"sandbox","k2.exe");
            using(var hash=SHA256.Create())using(var f=File.OpenRead(exe))
                if(BitConverter.ToString(hash.ComputeHash(f)).Replace("-","")!="1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45")throw new InvalidOperationException("Версия k2.exe отличается от проверенной.");
            if(!File.Exists(Path.Combine(root,"sandbox","terrain-prototype.marker")))throw new InvalidOperationException("Не найдена отдельная тестовая папка.");
            game=Process.Start(new ProcessStartInfo(exe) { WorkingDirectory=Path.GetDirectoryName(exe),UseShellExecute=false });
            await Task.Run(()=>AttachOwnedProcess());
            Log("Attached own PID="+game.Id+" image="+image.ToString("X8")+" cave="+cave.ToString("X8"));status.Text="Тест подключён. Создайте одиночную партию Paw's Terrain Test.";timer.Start();
        }
        catch(Exception ex){status.Text=ex.Message;Log(ex.ToString());launch.Enabled=true;}
        finally { attaching=false; }
    }
    void AttachOwnedProcess()
    {
        var j=new JavaScriptSerializer();var m=j.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(root,"native","prototype.json")));
        uint site=N(m["hook"]);var old=Enumerable.Range(0,5).Select(i=>Convert.ToByte(((string)m["before"]).Substring(i*2,2),16)).ToArray();
        if(handle!=IntPtr.Zero)CloseHandle(handle);
        handle=OpenProcess(0xc38,false,game.Id);if(handle==IntPtr.Zero)throw new IOException("Не удалось открыть собственный тестовый процесс.");
        bool ready=false;for(int i=0;i<400&&!game.HasExited;i++)
        {
            try { game.Refresh();image=unchecked((uint)game.MainModule.BaseAddress.ToInt32());if(Read(image+site,5).SequenceEqual(old)){ready=true;break;} } catch { }
            System.Threading.Thread.Sleep(50);
        }
        if(!ready)throw new InvalidOperationException("Игра не подготовила ожидаемый код 1.3.72; тест не подключён.");
        // Stop only our child briefly so no thread can execute a partially written hook.
        if(NtSuspendProcess(handle)!=0)throw new IOException("Не удалось безопасно подключить тест.");
        try
        {
            if(!Read(image+site,5).SequenceEqual(old))throw new InvalidOperationException("Точка подключения уже изменена.");
            cave=unchecked((uint)VirtualAllocEx(handle,IntPtr.Zero,N(m["size"]),0x3000,0x40).ToInt32());if(cave==0)throw new IOException("Нет памяти для теста.");
            byte[] code=File.ReadAllBytes(Path.Combine(root,"native","prototype.bin"));
            foreach(object entry in (IEnumerable)m["fixups"])
            {
                var f=(IList)entry;int off=Convert.ToInt32(f[0]);long delta=Convert.ToInt32(f[1])*((long)image-0x460000)+Convert.ToInt32(f[2])*((long)cave-0x10000000);
                Array.Copy(BitConverter.GetBytes(unchecked((uint)(BitConverter.ToUInt32(code,off)+delta))),0,code,off,4);
            }
            Write(cave,code);state=cave+N(m["state"]);W(state,image);W(state+4,cave+N(m["adapter"]));
            byte[] jump=new byte[5];jump[0]=0xe9;Array.Copy(BitConverter.GetBytes(unchecked(cave+N(m["entry"])-image-site-5)),0,jump,1,4);
            uint protect;if(!VirtualProtectEx(handle,P(image+site),5,0x40,out protect))throw new IOException("Точка теста недоступна для записи.");
            try { Write(image+site,jump);FlushInstructionCache(handle,P(image+site),5); }
            finally { uint unused;VirtualProtectEx(handle,P(image+site),5,protect,out unused); }
        }
        finally { NtResumeProcess(handle); }
    }
    void Poll()
    {
        if(busy||state==0)return;busy=true;
        try
        {
            if(game.HasExited){timer.Stop();actions.Enabled=false;launch.Enabled=true;status.Text="Тестовая игра закрыта. Журнал: probe.log";return;}
            var b=Read(state,92);last=Enumerable.Range(0,23).Select(i=>BitConverter.ToUInt32(b,i*4)).ToArray();
            uint currentWorld=U(image+0x5f3fb8),session=U(image+0x5f3fe4);
            bool valid=currentWorld!=0&&currentWorld==last[11]&&session!=0&&U(session+0xf0)==2&&Read(session+0x100,1)[0]==0&&last[13]>0&&last[13]<=128&&last[14]>0&&last[14]<=128;
            actions.Enabled=valid&&last[2]==last[3];if(!valid){status.Text="Ожидание маленькой одиночной карты Paw's Terrain Test.";return;}
            status.Text="Клеток: "+last[13]+" × "+last[14]+". Шагов: "+last[15]+"\n"+(last[2]!=last[3]?"Команда ждёт: вернитесь в игру и снимите паузу.":last[2]==0?"Можно выбрать участок и покрытие.":last[4]==0?"Покрытие изменено. Клеток с выбранным видом: "+last[16]:"Команда отклонена, код "+last[4]);
            if(last[3]>0&&(int)last[3]!=lastLogged){lastLogged=(int)last[3];Log("Result "+string.Join(",",last.Select(v=>v.ToString())));}
            uint array=U(last[12]+0x28);int w=(int)last[13],h=(int)last[14];byte[] cells=Read(array,w*h*0x30);var bitmap=new Bitmap(w,h);
            for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++)
            {
                uint flags=BitConverter.ToUInt32(cells,(yy*w+xx)*0x30+0x20);uint v=BitConverter.ToUInt32(cells,(yy*w+xx)*0x30);
                Color color=(flags&0x100)!=0?Color.SteelBlue:Color.SeaGreen;if(v==last[19]&&last[10]==2)color=Color.SandyBrown;
                if(xx>=(int)x.Value&&xx<(int)(x.Value+width.Value)&&yy>=(int)y.Value&&yy<(int)(y.Value+height.Value))color=Color.Gold;
                bitmap.SetPixel(xx,yy,color);
            }
            var previous=mapView.Image;mapView.Image=bitmap;if(previous!=null)previous.Dispose();
        }
        catch(Exception ex){actions.Enabled=false;status.Text=ex.Message;}
        finally{busy=false;}
    }
    void PaintTerrain(uint kind)
    {
        try
        {
            if(last==null||last[2]!=last[3])return;
            uint x0=(uint)x.Value,y0=(uint)y.Value,x1=x0+(uint)width.Value-1,y1=y0+(uint)height.Value-1;
            if(x1>=last[13]||y1>=last[14]||(x1-x0+1)*(y1-y0+1)>2048){status.Text="Участок должен находиться внутри карты и занимать до 2048 клеток.";return;}
            // Publish fields first and the aligned command serial last.
            uint[] fields={last[11],x0,y0,x1,y1,kind};var bytes=new byte[fields.Length*4];Buffer.BlockCopy(fields,0,bytes,0,bytes.Length);Write(state+20,bytes);
            serial=Math.Max(serial,(int)last[2])+1;W(state+8,(uint)serial);actions.Enabled=false;
            Log("Request "+serial+" kind="+kind+" rect="+x0+","+y0+","+x1+","+y1);
        }
        catch(Exception ex){status.Text=ex.Message;Log(ex.ToString());}
    }
}
