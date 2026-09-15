using System;
using System.Drawing;
using System.Drawing.Text;
using System.IO;
using System.Runtime.InteropServices;
class FontCoverageTests
{
    [DllImport("gdi32.dll",CharSet=CharSet.Unicode)]static extern uint GetGlyphIndicesW(IntPtr dc,string s,int n,[Out]ushort[] glyphs,uint flags);
    [DllImport("gdi32.dll")]static extern IntPtr SelectObject(IntPtr dc,IntPtr obj);
    [DllImport("gdi32.dll")]static extern bool DeleteObject(IntPtr obj);
    [DllImport("gdi32.dll",CharSet=CharSet.Unicode)]static extern int AddFontResourceEx(string path,uint flags,IntPtr reserved);
    [DllImport("gdi32.dll",CharSet=CharSet.Unicode)]static extern bool RemoveFontResourceEx(string path,uint flags,IntPtr reserved);
    static void Main(string[] args)
    {
        string sample="ČčŘřĚěŤťĎďŇňŮůÁáÉéÍíÓóÚúÝýŠšŽžҐґЄєІіЇїАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЮЯабвгдежзийклмнопрстуфхцчшщьюя’–—…→";
        int count=0,y=15;
        using(var bitmap=new Bitmap(1100,340))using(var graphics=Graphics.FromImage(bitmap))
        {
            graphics.Clear(Color.FromArgb(15,29,45));
            foreach(var path in Directory.GetFiles(args[0],"*.TTF"))
            using(var collection=new PrivateFontCollection())
            {
                if(AddFontResourceEx(path,0x10,IntPtr.Zero)==0)throw new Exception("Private GDI font load failed.");
                collection.AddFontFile(path);var family=collection.Families[0];
                using(var font=new Font(family,20,family.IsStyleAvailable(FontStyle.Regular)?FontStyle.Regular:FontStyle.Bold))
                {
                    IntPtr dc=graphics.GetHdc(),hfont=font.ToHfont(),old=SelectObject(dc,hfont);
                    try
                    {
                        var glyphs=new ushort[sample.Length];if(GetGlyphIndicesW(dc,sample,sample.Length,glyphs,1)==uint.MaxValue)throw new Exception("GDI glyph lookup failed.");
                        for(int i=0;i<glyphs.Length;i++){count++;if(glyphs[i]==0xffff)throw new Exception(Path.GetFileName(path)+" missing "+sample[i]);}
                    }
                    finally{SelectObject(dc,old);DeleteObject(hfont);graphics.ReleaseHdc(dc);}
                    graphics.DrawString(Path.GetFileName(path)+" — Červená, město, příjem, staveniště",font,Brushes.White,10,y);
                    graphics.DrawString("Українська: Ґанок, єдність, їжа, місто, м'ятний",font,Brushes.Gold,10,y+35);y+=105;
                }
                RemoveFontResourceEx(path,0x10,IntPtr.Zero);
            }
            bitmap.Save(args[1],System.Drawing.Imaging.ImageFormat.Png);
        }
        Console.WriteLine("FONT_GDI_PASS "+count+" actual glyph lookups; no game/window started.");
    }
}
