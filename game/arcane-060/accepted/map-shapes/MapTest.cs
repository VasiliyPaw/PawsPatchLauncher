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
    readonly ComboBox language=new ComboBox { DropDownStyle=ComboBoxStyle.DropDownList,Width=170 };
    readonly string[] languages={"en","ru","de","fr","cs","uk"};
    int selectedLanguage;
    bool roadsMode;
    bool bridgesMode;
    uint roadsState;
    readonly Timer timer=new Timer { Interval=500 };
    Process game;IntPtr handle;uint image,cave,state;bool busy,attaching;uint[] last;int lastLogged=-1;
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
        var metadata=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(root,"native","prototype.json")));
        roadsMode=metadata.ContainsKey("roadState")&&N(metadata["roadState"])!=0;
        bridgesMode=metadata.ContainsKey("bridges")&&Convert.ToBoolean(metadata["bridges"]);
        Text=roadsMode?"Paw's Roads — дороги инженерами":"Paw's Maps — форма и климат";ClientSize=new Size(700,300);MinimumSize=new Size(700,330);Font=new Font("Segoe UI",10);
        if(bridgesMode){Text="Paw's Bridges — переправы инженерами";ClientSize=new Size(700,340);MinimumSize=new Size(700,370);}
        var top=new FlowLayoutPanel { Dock=DockStyle.Top,AutoSize=true };top.Controls.Add(launch);
#if PAWS_BRIDGE_FIXTURE
        var fixture=new Button { Text="Учебная река",AutoSize=true };
        fixture.Click+=(s,e)=>{if(roadsState!=0&&game!=null&&!game.HasExited)W(roadsState+19280,1);};top.Controls.Add(fixture);
#endif
        language.Items.AddRange(new object[]{"English","Русский","Deutsch","Français","Čeština","Українська"});
        int saved;language.SelectedIndex=File.Exists(Path.Combine(root,"language.txt"))&&int.TryParse(File.ReadAllText(Path.Combine(root,"language.txt")),out saved)&&saved>=0&&saved<6?saved:1;
        top.Controls.Add(language);
        var help=new Label { Dock=DockStyle.Fill,Padding=new Padding(8),Text="Одиночная игра → новая партия → новая карта:\nотдельный выбор климата и формы карты.\n\nПангея / Средиземноморье / Реки; три климата.\nЯзык справа меняет новые пункты; остальная игра — английская.\nРазмеры новых форм: 384–1024. Только одиночная игра.\nОсновная установка и обычные сохранения не изменяются." };
        status.Height=110;
        if(roadsMode)help.Text="Single Player → Custom → значок дискеты → Engineers-ready → Launch.\nВыделите инженеров → «Строить дорогу» → протяните участок левой кнопкой мыши.\nОтпустите кнопку — инженеры начнут строить намеченный участок.\nПКМ / Esc отменяют план. Кнопка останавливает строительство.\n\nДорога: +20% базовой скорости. Готовое покрытие сохраняется.\nПока доступны прямые участки в одиночной тестовой игре.\nОсновная установка и обычные сохранения не изменяются.";
        Controls.Add(help);Controls.Add(status);Controls.Add(top);
        if(bridgesMode)help.Text="Single Player → Custom → дискета → Bridge-ready → Launch.\nВыделите инженеров → «Строить мост» → протяните от своего берега к другому.\nОтпустите кнопку. Инженеры подойдут к началу и построят переправу.\nПКМ / Esc отменяют план; кнопка останавливает стройку.\n\nТестовый настил использует рельеф; модели с опорами пока нет.\nТолько узкие прямые переправы в одиночной игре.\nОбычные дороги также доступны. Основная установка не изменяется.";
        status.Text="Отдельная копия игры готова. Основная установка не используется.";
        launch.Click+=async(s,e)=>await Launch();timer.Tick+=(s,e)=>Poll();
        FormClosed+=(s,e)=>{timer.Stop();if(handle!=IntPtr.Zero)CloseHandle(handle);};
        FormClosing+=(s,e)=>{if(attaching){e.Cancel=true;status.Text="Подключение теста завершается. Подождите несколько секунд.";}};
    }
    async Task Launch()
    {
        if(game!=null&&!game.HasExited)return;launch.Enabled=false;language.Enabled=false;selectedLanguage=language.SelectedIndex;attaching=true;lastLogged=-1;status.Text="Запускается отдельная копия игры…";
        try
        {
            string exe=Path.Combine(root,"sandbox","k2.exe");
            using(var hash=SHA256.Create())using(var f=File.OpenRead(exe))
                if(BitConverter.ToString(hash.ComputeHash(f)).Replace("-","")!="1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45")throw new InvalidOperationException("Версия k2.exe отличается от проверенной.");
            if(!File.Exists(Path.Combine(root,"sandbox","terrain-prototype.marker")))throw new InvalidOperationException("Не найдена отдельная тестовая папка.");
            string locale=Path.Combine(root,"locales",languages[selectedLanguage]);
            if(Directory.Exists(locale))foreach(string file in Directory.GetFiles(locale,"*",SearchOption.AllDirectories))
            {
                string destination=Path.Combine(root,"sandbox","probe-data",file.Substring(locale.Length+1));
                Directory.CreateDirectory(Path.GetDirectoryName(destination));File.Copy(file,destination,true);
            }
            File.WriteAllText(Path.Combine(root,"language.txt"),selectedLanguage.ToString());
            game=Process.Start(new ProcessStartInfo(exe) { WorkingDirectory=Path.GetDirectoryName(exe),UseShellExecute=false });
            await Task.Run(()=>AttachOwnedProcess());
            Log("Attached own PID="+game.Id+" image="+image.ToString("X8")+" cave="+cave.ToString("X8"));status.Text="Тест подключён. В новой одиночной партии выберите форму карты и климат.";timer.Start();
        }
        catch(Exception ex){status.Text=ex.Message;Log(ex.ToString());launch.Enabled=true;language.Enabled=true;}
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
            var patches=new List<Tuple<uint,byte[],uint,bool>>();
            foreach(object item in (IEnumerable)m["hooks"])
            {
                var hook=(Dictionary<string,object>)item;string hex=(string)hook["before"];bool pointer=(string)hook["kind"]=="pointer";
                byte[] expected=Enumerable.Range(0,hex.Length/2).Select(i=>Convert.ToByte(hex.Substring(i*2,2),16)).ToArray();
                if(pointer)expected=BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(expected,0)+image-0x460000));
                uint address=image+N(hook["site"]);
                if(!Read(address,expected.Length).SequenceEqual(expected))throw new InvalidOperationException("Точка подключения уже изменена: "+address.ToString("X8"));
                patches.Add(Tuple.Create(address,expected,N(hook["entry"]),pointer));
            }
            cave=unchecked((uint)VirtualAllocEx(handle,IntPtr.Zero,N(m["size"]),0x3000,0x40).ToInt32());if(cave==0)throw new IOException("Нет памяти для теста.");
            byte[] code=File.ReadAllBytes(Path.Combine(root,"native","prototype.bin"));
            foreach(object entry in (IEnumerable)m["fixups"])
            {
                var f=(IList)entry;int off=Convert.ToInt32(f[0]);long delta=Convert.ToInt32(f[1])*((long)image-0x460000)+Convert.ToInt32(f[2])*((long)cave-0x10000000);
                Array.Copy(BitConverter.GetBytes(unchecked((uint)(BitConverter.ToUInt32(code,off)+delta))),0,code,off,4);
            }
            Write(cave,code);state=cave+N(m["state"]);W(state,image);W(state+4,cave+N(m["adapter"]));
            if(m.ContainsKey("uiState")&&N(m["uiState"])!=0){W(cave+N(m["uiState"]),image);W(cave+N(m["uiState"])+4,(uint)selectedLanguage);}
            if(m.ContainsKey("roadState")&&N(m["roadState"])!=0){roadsState=cave+N(m["roadState"]);W(roadsState,image);W(roadsState+4,cave+N(m["adapter"]));W(roadsState+8,(uint)selectedLanguage);}
            var touched=new List<Tuple<uint,byte[],uint,bool>>();
            try
            {
                foreach(var patch in patches)
                {
                    byte[] replacement=patch.Item4?BitConverter.GetBytes(cave+patch.Item3):Enumerable.Repeat((byte)0x90,patch.Item2.Length).ToArray();
                    if(!patch.Item4){replacement[0]=0xe8;Array.Copy(BitConverter.GetBytes(unchecked(cave+patch.Item3-patch.Item1-5)),0,replacement,1,4);}
                    touched.Add(patch);ProtectedWrite(patch.Item1,replacement);
                }
            }
            catch
            {
                foreach(var patch in touched.AsEnumerable().Reverse())ProtectedWrite(patch.Item1,patch.Item2);
                throw;
            }
        }
        finally { NtResumeProcess(handle); }
    }
    void ProtectedWrite(uint address,byte[] bytes)
    {
        uint protect;if(!VirtualProtectEx(handle,P(address),(uint)bytes.Length,0x40,out protect))throw new IOException("Точка теста недоступна для записи.");
        try { Write(address,bytes);if(!FlushInstructionCache(handle,P(address),(uint)bytes.Length))throw new IOException("Не удалось обновить код теста."); }
        finally { uint unused;VirtualProtectEx(handle,P(address),(uint)bytes.Length,protect,out unused); }
    }
    void Poll()
    {
        if(busy||state==0)return;busy=true;
        try
        {
            if(game.HasExited){timer.Stop();launch.Enabled=true;language.Enabled=true;status.Text="Тестовая игра закрыта. Журнал: probe.log";return;}
            if(roadsState!=0){status.Text=(bridgesMode?"Тест дорог и переправ подключён.":"Тест дорог подключён.")+" Выберите инженеров в одиночном матче.\n"+"Обработано участков покрытия: "+U(roadsState+24)+". Завершено/отменено маршрутов: "+U(roadsState+20)+".";return;}
            var b=Read(state,64);last=Enumerable.Range(0,16).Select(i=>BitConverter.ToUInt32(b,i*4)).ToArray();
            if(last[12]==0){status.Text="Тест подключён. В новой одиночной партии выберите форму карты и климат.";return;}
            status.Text="Генерация: "+last[4]+". Клеток: "+last[6]+" × "+last[7]+". Этап: "+last[13]+"\n"+
                "Seed: "+last[5]+". Суша: "+last[9]+"; вода: "+last[10]+".\n"+
                (last[13]==5&&last[8]==0?"Форма создана; размещение объектов завершает сама игра.":"Код: "+last[8]);
            int key=(int)(last[12]*100+last[13]);if(key!=lastLogged){lastLogged=key;Log("Generation "+string.Join(",",last.Select(v=>v.ToString())));}
        }
        catch(Exception ex){status.Text=ex.Message;}
        finally{busy=false;}
    }
}
