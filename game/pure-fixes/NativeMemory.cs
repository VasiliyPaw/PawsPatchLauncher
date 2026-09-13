using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace PawPureFixes
{
    internal sealed class NativeMemory : IPatchMemory, IDisposable
    {
        private IntPtr handle;
        private bool suspended;
        internal NativeMemory(int pid, string expectedPath, DateTime verifiedStart)
        {
            handle = OpenProcess(0x0008 | 0x0010 | 0x0020 | 0x0400 | 0x0800, false, pid);
            if (handle == IntPtr.Zero) Fail("OpenProcess");
            try
            {
                // Validate the actual native handle, not merely a PID that
                // could have been recycled between discovery and OpenProcess.
                long created, exited, kernel, user;
                if (!GetProcessTimes(handle, out created, out exited, out kernel, out user)) Fail("GetProcessTimes");
                StringBuilder path = new StringBuilder(32768); int length = path.Capacity;
                if (!QueryFullProcessImageName(handle, 0, path, ref length)) Fail("QueryFullProcessImageName");
                if (DateTime.FromFileTimeUtc(created) != verifiedStart ||
                    !String.Equals(Path.GetFullPath(path.ToString()), Path.GetFullPath(expectedPath), StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("The opened process handle does not match the verified fresh launch.");
            }
            catch { CloseHandle(handle); handle = IntPtr.Zero; throw; }
        }
        private static IntPtr Ptr(uint address) { return new IntPtr(unchecked((int)address)); }
        private static void Fail(string operation) { throw new Win32Exception(Marshal.GetLastWin32Error(), operation); }
        internal void Suspend()
        {
            int status = NtSuspendProcess(handle);
            if (status != 0) throw new InvalidOperationException("NtSuspendProcess 0x" + status.ToString("X8"));
            suspended = true;
        }
        internal void Resume()
        {
            if (!suspended) return;
            int status = NtResumeProcess(handle);
            if (status != 0) throw new InvalidOperationException("NtResumeProcess 0x" + status.ToString("X8"));
            suspended = false;
        }
        public byte[] Read(uint address, int count)
        {
            byte[] bytes = new byte[count]; IntPtr done;
            if (!ReadProcessMemory(handle, Ptr(address), bytes, new IntPtr(count), out done) || done.ToInt64() != count) Fail("ReadProcessMemory");
            return bytes;
        }
        public void Write(uint address, byte[] bytes)
        {
            IntPtr done;
            if (!WriteProcessMemory(handle, Ptr(address), bytes, new IntPtr(bytes.Length), out done) || done.ToInt64() != bytes.Length) Fail("WriteProcessMemory");
        }
        public void WriteCode(uint address, byte[] bytes)
        {
            uint old, ignored;
            if (!VirtualProtectEx(handle, Ptr(address), new IntPtr(bytes.Length), 0x40, out old)) Fail("VirtualProtectEx RWX");
            try { Write(address, bytes); }
            finally
            {
                if (!VirtualProtectEx(handle, Ptr(address), new IntPtr(bytes.Length), old, out ignored)) Fail("VirtualProtectEx restore");
            }
        }
        public uint Allocate(int count)
        {
            IntPtr pointer = VirtualAllocEx(handle, IntPtr.Zero, new IntPtr(count), 0x3000, 0x04);
            if (pointer == IntPtr.Zero) Fail("VirtualAllocEx");
            return unchecked((uint)pointer.ToInt32());
        }
        public void MakeExecutable(uint address, int count)
        {
            uint old;
            if (!VirtualProtectEx(handle, Ptr(address), new IntPtr(count), 0x20, out old)) Fail("VirtualProtectEx RX");
        }
        public void Flush(uint address, int count)
        {
            if (!FlushInstructionCache(handle, Ptr(address), new IntPtr(count))) Fail("FlushInstructionCache");
        }
        public void Free(uint address)
        {
            if (!VirtualFreeEx(handle, Ptr(address), IntPtr.Zero, 0x8000)) Fail("VirtualFreeEx");
        }
        public void Dispose()
        {
            try { Resume(); }
            finally
            {
                if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; }
            }
        }
        [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr OpenProcess(uint rights, bool inherit, int pid);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool ReadProcessMemory(IntPtr p, IntPtr a, byte[] b, IntPtr n, out IntPtr read);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool WriteProcessMemory(IntPtr p, IntPtr a, byte[] b, IntPtr n, out IntPtr written);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr VirtualAllocEx(IntPtr p, IntPtr a, IntPtr n, uint allocation, uint protection);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool VirtualFreeEx(IntPtr p, IntPtr a, IntPtr n, uint kind);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool VirtualProtectEx(IntPtr p, IntPtr a, IntPtr n, uint protection, out uint old);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool FlushInstructionCache(IntPtr p, IntPtr a, IntPtr n);
        [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetProcessTimes(IntPtr p, out long created, out long exited, out long kernel, out long user);
        [DllImport("kernel32.dll", EntryPoint = "QueryFullProcessImageNameW", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool QueryFullProcessImageName(IntPtr p, uint flags, StringBuilder path, ref int length);
        [DllImport("ntdll.dll")] private static extern int NtSuspendProcess(IntPtr handle);
        [DllImport("ntdll.dll")] private static extern int NtResumeProcess(IntPtr handle);
    }
}
