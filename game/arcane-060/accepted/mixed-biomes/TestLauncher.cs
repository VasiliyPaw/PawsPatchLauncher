using System;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Windows.Forms;
internal static class MixedTestLauncher
{
    [STAThread] static void Main()
    {
        try
        {
            string root=AppDomain.CurrentDomain.BaseDirectory;
            string game=Path.Combine(root,"game");
            string marker=Path.Combine(game,"reconnect-test.marker");
            if(!File.Exists(marker)||File.ReadAllText(marker).Trim()!="Private mixed-biomes test only")
                throw new IOException("Не найдена отдельная тестовая копия игры.");
            if(Process.GetProcessesByName("k2").Length!=0)
                throw new InvalidOperationException("Сначала закройте запущенную Kohan II, затем запустите тестовую сборку.");
            using(var sha=SHA256.Create())using(var input=File.OpenRead(Path.Combine(game,"k2.exe")))
                if(BitConverter.ToString(sha.ComputeHash(input)).Replace("-","")!="1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45")
                    throw new IOException("Тестовая копия k2.exe отличается от проверенной версии 1.3.72.");
            Directory.CreateDirectory(Path.Combine(root,"Documents"));Directory.CreateDirectory(Path.Combine(root,"AppData"));
            var start=new ProcessStartInfo(Path.Combine(game,"k2_paws_ui_1372.exe"),"--game-dir \""+game+"\"");
            start.WorkingDirectory=game;start.UseShellExecute=false;start.CreateNoWindow=true;start.WindowStyle=ProcessWindowStyle.Hidden;
            start.EnvironmentVariables["PAWS_TEST_DOCUMENTS"]=Path.Combine(root,"Documents");
            start.EnvironmentVariables["PAWS_TEST_APPDATA"]=Path.Combine(root,"AppData");
            start.EnvironmentVariables["SteamAppId"]="97130";start.EnvironmentVariables["SteamGameId"]="97130";
            start.EnvironmentVariables.Remove("PAWS_TEST_JOIN");start.EnvironmentVariables.Remove("PAWS_RIG_EXTERNAL_SCRIPT");
            Process.Start(start);
        }
        catch(Exception e){MessageBox.Show(e.Message,"Paw’s Patch — тест смешанных биомов");}
    }
}
