using System;
using System.IO;
using System.Reflection;

// Compile as a .NET Framework console program so the shipped helper's exact
// compatibility implementation runs with its original framework dependencies.
class FactionCompatibilityProbe
{
    static int Main(string[] args)
    {
        try
        {
            var helper = Assembly.LoadFrom(Path.GetFullPath(args[0]));
            var identity = helper.GetType("PawLobbyCompatibility", true).GetMethod("InstalledIdentity", BindingFlags.NonPublic | BindingFlags.Static);
            var baseline = (string)identity.Invoke(null, new object[] { Path.GetFullPath(args[1]), false });
            var custom = (string)identity.Invoke(null, new object[] { Path.GetFullPath(args[2]), false });
            if (baseline != custom) throw new Exception("Personal faction voices changed multiplayer compatibility: " + baseline + " != " + custom);
            Console.WriteLine("SHIPPED HELPER COMPATIBILITY PASS: installed state accepted; gameplay identity unchanged: " + custom);
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
