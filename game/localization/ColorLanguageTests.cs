using System;
using System.Globalization;
using System.Reflection;
using System.Threading;
class ColorLanguageTests
{
    static void Main(string[] args)
    {
        string[] codes={"en","ru","de","fr","cs","uk"};
        string[] reds={"Red","Красный","Rot","Rouge","Červená","Червоний"};
        int index=Array.IndexOf(codes,args[0]);if(index<0)throw new Exception("Test language missing.");
        Thread.CurrentThread.CurrentUICulture=new CultureInfo(args[0]=="ru"?"en-US":"ru-RU");
        if(PawGameText.Language!=args[0]||PawGameText.LanguageId!=(uint)index)throw new Exception("Wrong applied text language.");
        if(PawGameText.Color("Красный","Red")!=reds[index])throw new Exception("Windows language overrode the applied language.");
        PawLobbyColorsNative.VerifyOffline();
        object palette=typeof(PawLobbyColorsNative).GetMethod("LoadPalette",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
        var colors=(Array)palette.GetType().GetField("Colors",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).GetValue(palette);
        if(colors.Length!=49)throw new Exception("Palette changed.");
        object first=colors.GetValue(0);var type=first.GetType();
        if((string)type.GetField("Id").GetValue(first)!="paws_red"||(string)type.GetField("Name").GetValue(first)!=reds[index]||(byte)type.GetField("R").GetValue(first)!=242)throw new Exception("Native palette changed.");
        Console.WriteLine("COLOR_LANGUAGE_PASS "+args[0]+"; opposite Windows language, 49 colors, native payload and RGB preserved");
    }
}
