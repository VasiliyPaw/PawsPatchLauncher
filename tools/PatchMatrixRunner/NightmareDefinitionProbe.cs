using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

// Read-only oracle for the verified 1.3.7.2 test process selected by the runner.
// Reads database definitions at the main menu, without editing lobby settings.
internal static class NightmareDefinitionProbe
{
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern SafeProcessHandle OpenProcess(uint access, bool inherit, int pid);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool ReadProcessMemory(SafeProcessHandle process, IntPtr address, byte[] buffer, nuint count, out nuint read);
    public static string[] Read(Process process)
    {
        uint image = checked((uint)process.MainModule!.BaseAddress.ToInt64());
        using var handle = OpenProcess(0x1010, false, process.Id);
        if (handle.IsInvalid) throw new IOException("Cannot read test process.");
        byte[] Bytes(uint address, int count)
        {
            if (address < 0x10000 || count < 1 || count > 1024 || (ulong)address + (uint)count > uint.MaxValue) throw new InvalidDataException("Invalid database pointer.");
            var buffer = new byte[count];
            if (!ReadProcessMemory(handle, new IntPtr(address), buffer, (nuint)count, out var read) || read != (nuint)count) throw new IOException("Incomplete database read.");
            return buffer;
        }
        uint U32(uint address) => BitConverter.ToUInt32(Bytes(address, 4));
        if (U32(image + U32(image + 0x3c) + 8) != 0x6a9750c7) throw new InvalidDataException("Unsupported image timestamp.");
        uint db = U32(image + 0x5f3fb4), count = U32(db + 0x440), list = U32(db + 0x43c);
        if (count is < 5 or > 6) throw new InvalidDataException("Unexpected handicap count: " + count);
        var names = new List<string>();
        for (uint i = 0; i < count; i++)
        {
            uint text = U32(U32(list + i * 4) + 8);
            var bytes = new List<byte>(); bool terminated = false;
            for (uint j = 0; j < 128; j++)
            {
                var pair = Bytes(text + j * 2, 2);
                if (pair[0] == 0 && pair[1] == 0) { terminated = true; break; }
                bytes.AddRange(pair);
            }
            if (!terminated) throw new InvalidDataException("Unterminated handicap name.");
            names.Add(Encoding.Unicode.GetString(bytes.ToArray()));
        }
        return names.ToArray();
    }
}
