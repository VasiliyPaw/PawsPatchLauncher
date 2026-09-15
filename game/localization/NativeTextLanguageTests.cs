using System;
using System.Globalization;
using System.Threading;

class NativeTextLanguageTests
{
    static void Main(string[] args)
    {
        string code=args[0];
        if(code!="de"&&code!="fr")throw new Exception("Expected a changed native catalog.");
        Thread.CurrentThread.CurrentUICulture=new CultureInfo("ru-RU");
        string[] source={"City Auto-Upgrade","Apply","Cancel","Cities"};
        string[] expected=code=="de"
            ?new[]{"Automatischer Stadtausbau","Übernehmen","Abbrechen","Städte"}
            :new[]{"Amélioration automatique des villes","Appliquer","Annuler","Villes"};
        if(PawGameText.Language!=code)throw new Exception("Wrong game text selection.");
        for(int i=0;i<source.Length;i++)
            if(PawGameText.Text("Неверный резервный текст",source[i],true)!=expected[i])
                throw new Exception("Native UI used the wrong language: "+source[i]);
        if(PawGameText.Text("Неверный резервный текст","unknown-key",true)!="unknown-key")
            throw new Exception("Windows locale overrode the explicitly selected game text.");
        Console.WriteLine("NATIVE_TEXT_PASS "+code+": title, actions, city tab and language fallback independent of Windows");
    }
}
