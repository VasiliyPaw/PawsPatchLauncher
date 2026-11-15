using System;using System.IO;
internal static class PawRuntimePaths {
 static string Resolve(string variable,Environment.SpecialFolder fallback){string p=Environment.GetEnvironmentVariable(variable);return string.IsNullOrWhiteSpace(p)?Environment.GetFolderPath(fallback):Path.GetFullPath(p);}
 internal static string Documents {get{return Resolve("PAWS_TEST_DOCUMENTS",Environment.SpecialFolder.MyDocuments);}}
 internal static string AppData {get{return Resolve("PAWS_TEST_APPDATA",Environment.SpecialFolder.LocalApplicationData);}}
}
