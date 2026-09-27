using System;
using System.Runtime.InteropServices;

namespace RacingBois.Diagnostics.NativeBaseline
{
    /// <summary>Current-process Windows counters; no process enumeration or foreign handle access.</summary>
    internal static class NativeProcessMemory
    {
        internal const string Api = "GetProcessMemoryInfo / PROCESS_MEMORY_COUNTERS_EX";
        [StructLayout(LayoutKind.Sequential)]
        private struct Counters
        {
            public uint cb, PageFaultCount;
            public UIntPtr PeakWorkingSetSize, WorkingSetSize, QuotaPeakPagedPoolUsage, QuotaPagedPoolUsage;
            public UIntPtr QuotaPeakNonPagedPoolUsage, QuotaNonPagedPoolUsage, PagefileUsage, PeakPagefileUsage, PrivateUsage;
        }
        internal static int StructureBytes => Marshal.SizeOf<Counters>();
        internal static bool TryRead(out long workingSet, out long privateBytes, out int error)
        {
            workingSet = privateBytes = 0; error = 0;
            if (IntPtr.Size != 8 || StructureBytes != 80) { error = -1; return false; }
            try
            {
                var counters = new Counters { cb = (uint)StructureBytes };
                if (!GetProcessMemoryInfo(GetCurrentProcess(), ref counters, counters.cb))
                { error = Marshal.GetLastWin32Error(); if (error == 0) error = -5; return false; }
                ulong working = counters.WorkingSetSize.ToUInt64(), committed = counters.PrivateUsage.ToUInt64();
                if (working == 0 || committed == 0 || working > long.MaxValue || committed > long.MaxValue)
                { error = -2; return false; }
                workingSet = (long)working; privateBytes = (long)committed; return true;
            }
            catch (DllNotFoundException) { error = -3; return false; }
            catch (EntryPointNotFoundException) { error = -4; return false; }
        }
        // This is a pseudo-handle owned by the OS, and must not be closed.
        [DllImport("kernel32.dll", ExactSpelling = true)]
        private static extern IntPtr GetCurrentProcess();
        [DllImport("psapi.dll", ExactSpelling = true, SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool GetProcessMemoryInfo(IntPtr process, ref Counters counters, uint bytes);
    }
}
