using System;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Windows.Forms;

// Opens only the prepared private copy. The native marker/byte guards install
// the bridge module; no attachment to the installed game or existing process.
internal static class BridgeTest
{
    [STAThread] private static void Main()
    {
        try
        {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string directory = Path.Combine(root, "sandbox");
            string exe = Path.Combine(directory, "k2.exe");
            if (!File.Exists(Path.Combine(directory, "terrain-prototype.marker"))
                || !File.Exists(Path.Combine(directory, "Mods", "PawsBridges.dll")))
                throw new IOException("Не найдена отдельная тестовая копия с модулем мостов.");
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(exe))
                if (BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "")
                    != "1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45")
                    throw new IOException("Версия тестовой игры отличается от проверенной 1.3.72.");
            foreach (Process process in Process.GetProcessesByName("k2"))
            {
                try
                {
                    if (String.Equals(process.MainModule.FileName, exe, StringComparison.OrdinalIgnoreCase))
                    {
                        MessageBox.Show("Эта тестовая копия уже запущена.", "Тест мостов");
                        return;
                    }
                }
                catch (System.ComponentModel.Win32Exception) { }
                catch (InvalidOperationException) { }
                finally { process.Dispose(); }
            }
            bool installed = File.Exists(Path.Combine(directory, "installed-runtime.marker"));
            string helper = Path.Combine(directory, "PawsInstalledRuntime.exe");
            if (installed && !File.Exists(helper))
                throw new IOException("Не найден полный набор исправлений тестовой игры.");
            var start = new ProcessStartInfo(installed ? helper : exe)
            {
                WorkingDirectory = directory,
                UseShellExecute = false,
                Arguments = installed ? "--game-dir \"" + directory + "\"" : ""
            };
            start.EnvironmentVariables["SteamAppId"] = "97130";
            start.EnvironmentVariables["SteamGameId"] = "97130";
            start.EnvironmentVariables["PAWS_TEST_DOCUMENTS"] = Path.Combine(root, "Documents");
            start.EnvironmentVariables["PAWS_TEST_APPDATA"] = Path.Combine(root, "AppData");
            string temporary = Path.Combine(root, "Temp");
            Directory.CreateDirectory(temporary);
            start.EnvironmentVariables["TEMP"] = temporary;
            start.EnvironmentVariables["TMP"] = temporary;
            Directory.CreateDirectory(start.EnvironmentVariables["PAWS_TEST_DOCUMENTS"]);
            Directory.CreateDirectory(start.EnvironmentVariables["PAWS_TEST_APPDATA"]);
            Process.Start(start);
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Не удалось запустить тест мостов", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
