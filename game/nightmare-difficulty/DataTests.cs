using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
internal static class ReleaseStartup {
 internal static string Hash(string path){using(var s=File.OpenRead(path))using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","");}
}
internal static class NightmareDataTests {
 static int checks;
 static void Check(bool value,string why){checks++;if(!value)throw new Exception(why);}
 static int Main(string[] args){
  string root=args[0], path=Path.Combine(root,"Local_ru/Localization/paws_nightmare.tgi");
  string def=Path.Combine(root,"data/Game/handicaps_paws_nightmare.tgi"), before=ReleaseStartup.Hash(def);
  // Exercise all actual generated catalogs, switches, idempotence and fallback.
  foreach(string lang in NightmareDifficultyData.Languages){
   byte[] installed=NightmareDifficultyData.Locales[Array.IndexOf(NightmareDifficultyData.Languages,lang)];
   File.WriteAllBytes(path,installed);
   NightmareDifficultyData.Prepare(root,lang,true);byte[] b=File.ReadAllBytes(path);
   Check(Convert.ToBase64String(b)==Convert.ToBase64String(NightmareDifficultyData.Locales[Array.IndexOf(NightmareDifficultyData.Languages,lang)]),lang);
   Check(b[0]==255&&b[1]==254,"UTF16 BOM");
   NightmareDifficultyData.Prepare(root,lang,true);Check(Convert.ToBase64String(b)==Convert.ToBase64String(File.ReadAllBytes(path)),"repeat has no writes");
   Check(ReleaseStartup.Hash(def)==before,"definition unchanged");
  }
  NightmareDifficultyData.Prepare(root,"unknown",true);Check(ReleaseStartup.Hash(def)==before,"English fallback preserves data");
  byte[] good=File.ReadAllBytes(path);
  File.WriteAllText(path,"local modification",Encoding.Unicode);bool failed=false;
  try{NightmareDifficultyData.Prepare(root,"ru",true);}catch(InvalidDataException){failed=true;}
  Check(failed&&File.ReadAllText(path,Encoding.Unicode)=="local modification","modified localization preserved");File.WriteAllBytes(path,good);
  byte[] definition=File.ReadAllBytes(def);File.WriteAllText(def,"modified");failed=false;
  try{NightmareDifficultyData.Prepare(root,"ru",true);}catch(InvalidDataException){failed=true;}
  Check(failed,"invalid data refused");File.WriteAllBytes(def,definition);
  File.Move(def,def+".testbackup");failed=false;
  try{NightmareDifficultyData.Prepare(root,"ru",true);}catch(InvalidDataException){failed=true;}
  Check(failed,"missing data refused");File.Move(def+".testbackup",def);
  File.WriteAllBytes(path,NightmareDifficultyData.Locales[Array.IndexOf(NightmareDifficultyData.Languages,"ru")]);
  NightmareDifficultyData.Prepare(root,"ru",true);Check(ReleaseStartup.Hash(def)==before,"fixture restored");
  string prop=Path.Combine(root,"data/Properties/paws_handicap_nightmare.tgi");
  byte[] property=File.ReadAllBytes(prop);
  // Installer removes both gameplay definitions when AI improvements are disabled.
  foreach(bool keepDef in new[]{false,true})foreach(bool keepProp in new[]{false,true}){
   if(keepDef)File.WriteAllBytes(def,definition);else File.Delete(def);
   if(keepProp)File.WriteAllBytes(prop,property);else File.Delete(prop);
   failed=false;try{NightmareDifficultyData.Prepare(root,"ru",false);}catch(InvalidDataException){failed=true;}
   Check(failed==(keepDef||keepProp),"off rejects either leftover gameplay definition");
   Check(File.Exists(def)==keepDef&&File.Exists(prop)==keepProp,"guard never edits gameplay files");
  }
  File.Delete(def);File.Delete(prop);File.Delete(path);NightmareDifficultyData.Prepare(root,"ru",false);
  Check(!File.Exists(path),"off does not recreate localization");
  File.WriteAllBytes(def,definition);File.WriteAllBytes(prop,property);
  failed=false;try{NightmareDifficultyData.Prepare(root,"ru",true);}catch(InvalidDataException){failed=true;}
  Check(failed&&!File.Exists(path),"on requires installed locale without synthesizing it");
  File.WriteAllBytes(path,NightmareDifficultyData.Locales[Array.IndexOf(NightmareDifficultyData.Languages,"ru")]);
  NightmareDifficultyData.Prepare(root,"ru",true);
  Console.WriteLine("NIGHTMARE_DATA_PASS "+checks+" checks; six languages; fixtures only");return 0;
 }
}
