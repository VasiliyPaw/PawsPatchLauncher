using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;

// Imports ImageGen material plates into the existing HUD's unused minimap gutters.
// Geometry comes from the stock 1024x768 UI, NOT from generated images. No code,
// widget positions, hit regions, game rules or original painted ornaments change.
internal static class BuildMinimapAssets
{
    static readonly string[] Races = { "Human", "Gauri", "Drauga", "Haroun", "Undead", "Shadow" };
    static readonly string[] Titles = { "Люди", "Гаури", "Драуга", "Хароуны", "Нежить", "Тени" };
    static readonly string[] Variants = { "UI/Game/ControlPanel", "UI/800/Game/ControlPanel", "UI/1280/Game/ControlPanel" };
    static string Root;
    static double Aspect;
    static readonly List<string> Rows = new List<string>();

    sealed class Tga
    {
        public byte[] Raw;
        public int W, H, Offset;
        public bool Top, Right;
        public Tga(string path)
        {
            Raw = File.ReadAllBytes(path);
            if (Raw.Length < 18 || Raw[1] != 0 || Raw[2] != 2 || Raw[16] != 32)
                throw new InvalidDataException("Expected stock uncompressed BGRA TGA: " + path);
            W = BitConverter.ToUInt16(Raw, 12); H = BitConverter.ToUInt16(Raw, 14);
            Offset = 18 + Raw[0]; Top = (Raw[17] & 32) != 0; Right = (Raw[17] & 16) != 0;
            if (Offset + W * H * 4 > Raw.Length) throw new InvalidDataException(path);
        }
        int Index(int x, int y) { return Offset + ((Top ? y : H - 1 - y) * W + (Right ? W - 1 - x : x)) * 4; }
        public Color Get(int x, int y) { int p = Index(x, y); return Color.FromArgb(Raw[p+3], Raw[p+2], Raw[p+1], Raw[p]); }
        public void Set(int x, int y, Color c) { int p = Index(x, y); Raw[p]=c.B; Raw[p+1]=c.G; Raw[p+2]=c.R; Raw[p+3]=c.A; }
        public Bitmap Bitmap()
        {
            var b = new Bitmap(W,H,PixelFormat.Format32bppArgb);
            var bits = b.LockBits(new Rectangle(0,0,W,H), ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
            var row = new byte[W*4];
            for (int y=0;y<H;y++) {
                for(int x=0;x<W;x++) { Color c=Get(x,y); row[x*4]=c.B;row[x*4+1]=c.G;row[x*4+2]=c.R;row[x*4+3]=c.A; }
                System.Runtime.InteropServices.Marshal.Copy(row,0,IntPtr.Add(bits.Scan0,y*bits.Stride),row.Length);
            }
            b.UnlockBits(bits);return b;
        }
    }
    static string Sha(byte[] b) { using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-",""); }
    static string Find(string folder) {
        foreach(string p in Directory.GetFiles(folder)) if(Path.GetFileName(p).Equals("Background.tga",StringComparison.OrdinalIgnoreCase))return p;
        throw new FileNotFoundException(folder);
    }
    static int Channel(double x) { return Math.Max(0,Math.Min(255,(int)Math.Round(x))); }
    static double Diamond(int x,int y,double cx,double cy,double rx,double ry) { return Math.Abs(x+0.5-cx)/rx+Math.Abs(y+0.5-cy)/ry; }

    static void Build(string race, string variant)
    {
        string input=Find(Path.Combine(Root,"source",race,variant));
        var t=new Tga(input);byte[] before=(byte[])t.Raw.Clone();
        using(var original=t.Bitmap())
        // Stock fallback UI is Human at 1024, but Gauri at 800/1280.
        using(var material=new Bitmap(Path.Combine(Root,"materials",race=="Observer"&&variant!=Variants[0]?"Gauri.png":race+".png")))
        {
            // The game letterboxes its square minimap in a non-uniformly scaled UI.
            double cx=135.0*t.W/1024.0, cy=132.0*t.H/256.0;
            double rx=120.0*t.W/(768.0*Aspect), ry=120.0*t.H/256.0;
            // Flood only the dark, opaque hole, bounded by its stock diamond.
            var hole=new bool[t.W*t.H];var queue=new Queue<int>();
            int seed=(int)cy*t.W+(int)cx;hole[seed]=true;queue.Enqueue(seed);
            while(queue.Count>0) {
                int p=queue.Dequeue(),x=p%t.W,y=p/t.W;
                int[] xx={x-1,x+1,x,x}, yy={y,y,y-1,y+1};
                for(int n=0;n<4;n++) {
                    int a=xx[n],b=yy[n];if(a<0||b<0||a>=t.W||b>=t.H)continue;
                    int k=b*t.W+a;if(hole[k])continue;
                    // Do not enter other black panels or outside transparency.
                    if(Diamond(a,b,cx,cy,158*t.W/1280.0,158*t.H/320.0)>1)continue;
                    Color c=original.GetPixel(a,b);
                    if(c.A<255||Math.Max(c.R,Math.Max(c.G,c.B))>30)continue;
                    hole[k]=true;queue.Enqueue(k);
                }
            }
            int changed=0,insideChanges=0,outsideChanges=0;
            for(int y=0;y<t.H;y++)for(int x=0;x<Math.Min(t.W,(int)(356*t.W/1280.0));x++) {
                double d=Diamond(x,y,cx,cy,rx,ry);
                if(!hole[y*t.W+x]||d<=1.0+1e-10)continue;
                // Clip a real ImageGen plate to the geometric gutter. Sampling
                // remains square in physical screen pixels; it is not new art.
                double u=(x/(double)t.W*1280.0-12)/312.0;
                double v=y/(double)t.H;
                int mx=Math.Max(0,Math.Min(material.Width-1,(int)((0.13+u*0.74)*material.Width)));
                int my=Math.Max(0,Math.Min(material.Height-1,(int)((0.08+v*0.84)*material.Height)));
                Color c=material.GetPixel(mx,my);
                // A restrained bevel makes the aperture unambiguous even in fog.
                double distance=(d-1.0)/Math.Sqrt(1/(rx*rx)+1/(ry*ry));
                double shade=0.74;
                if(distance<1.1)shade=0.43;
                else if(distance<3.0)shade=(x<cx?1.10:0.88);
                Color result=Color.FromArgb(255,Channel(c.R*shade),Channel(c.G*shade),Channel(c.B*shade));
                t.Set(x,y,result);changed++;
            }
            // Pixel-level invariants: no change inside the map, no altered alpha,
            // no changed art outside the empty hole and no dimensions/header drift.
            for(int y=0;y<t.H;y++)for(int x=0;x<t.W;x++) {
                Color a=original.GetPixel(x,y),b=t.Get(x,y);
                if(a.A!=b.A)throw new Exception("Alpha changed");
                if(a.ToArgb()==b.ToArgb())continue;
                if(Diamond(x,y,cx,cy,rx,ry)<=1.0+1e-10)insideChanges++;
                if(!hole[y*t.W+x])outsideChanges++;
            }
            if(insideChanges!=0||outsideChanges!=0||changed<300)throw new Exception("Invalid gutter clip "+race+" "+variant);
            string relative=(race=="Observer"?"data/":"skins/"+race+"/")+variant+"/Background.tga";
            string target=Path.Combine(Root,"payload",relative);Directory.CreateDirectory(Path.GetDirectoryName(target));File.WriteAllBytes(target,t.Raw);
            string texturePreview=Path.Combine(Root,"previews","textures",Path.ChangeExtension(relative,".png"));
            Directory.CreateDirectory(Path.GetDirectoryName(texturePreview));
            using(var b=t.Bitmap())b.Save(texturePreview,ImageFormat.Png);
            string preview=Path.Combine(Root,"previews",race+"-original.png");
            if(variant==Variants[2]){original.Save(preview,ImageFormat.Png);using(var b=t.Bitmap())b.Save(Path.Combine(Root,"previews",race+"-fitted.png"),ImageFormat.Png);}
            Rows.Add(string.Join("\t",new[]{relative,t.W.ToString(),t.H.ToString(),changed.ToString(),Sha(before),Sha(t.Raw)}));
            Console.WriteLine(race+" "+variant+": "+changed+" gutter pixels; map, alpha, other artwork unchanged");
        }
    }
    static GraphicsPath Poly(PointF[] pts) { var p=new GraphicsPath();p.AddPolygon(pts);return p; }
    static PointF[] DiamondPoints(float cx,float cy,float rx,float ry) {
        return new[]{new PointF(cx,cy-ry),new PointF(cx+rx,cy),new PointF(cx,cy+ry),new PointF(cx-rx,cy)};
    }
    static Bitmap Preview(string race,bool fitted,Bitmap screenshot)
    {
        // Static UI composition, not a screenshot from a running game.
        // Stock HUD texture transform at 2560x1440: x*2, y*1.5, origin (0,960).
        var result=new Bitmap(710,544,PixelFormat.Format32bppArgb);
        using(var g=Graphics.FromImage(result)) {
            g.Clear(Color.FromArgb(35,43,27));g.InterpolationMode=InterpolationMode.HighQualityBicubic;
            // Neutral preview backdrop: copying the screenshot's world here
            // would also retain its original Drauga crest behind other skins.
            using(var bg=new Bitmap(Path.Combine(Root,"previews",race+(fitted?"-fitted.png":"-original.png"))))
                g.DrawImage(bg,new RectangleF(0,64,2560,480));
            using(var top=new Bitmap(Path.Combine(Root,"source",race,"UI/1280/Game/ControlPanel/BackgroundTop.png")))
                g.DrawImage(top,new RectangleF(252.5f,4,160,60));
            // The same observed terrain/camera rectangle is used on both sides.
            using(var clip=Poly(DiamondPoints(337.5f,311.5f,225f,225f))) {
                var state=g.Save();g.SetClip(clip);
                g.DrawImage(screenshot,new RectangleF(112.5f,86.5f,450,450),new RectangleF(112.5f,982.5f,450,450),GraphicsUnit.Pixel);
                g.Restore(state);
            }
            // Original controls from the user's screenshot, unchanged locations.
            RectangleF[] buttons={new RectangleF(40,1370.625f,72.5f,54.375f),new RectangleF(117.5f,1370.625f,72.5f,54.375f),new RectangleF(485,1370.625f,72.5f,54.375f),new RectangleF(562.5f,1370.625f,72.5f,54.375f)};
            foreach(var rect in buttons)g.DrawImage(screenshot,new RectangleF(rect.X,rect.Y-896,rect.Width,rect.Height),rect,GraphicsUnit.Pixel);
        }
        return result;
    }
    static void Previews(string screenshotPath)
    {
        using(var screenshot=new Bitmap(screenshotPath)) {
            if(screenshot.Width!=2560||screenshot.Height!=1440)throw new Exception("Reference screenshot dimensions changed");
            for(int page=0;page<2;page++)using(var sheet=new Bitmap(1460,1845))using(var g=Graphics.FromImage(sheet))
            using(var font=new Font("Segoe UI",22,FontStyle.Bold))using(var label=new Font("Segoe UI",16)) {
                g.Clear(Color.FromArgb(20,25,29));
                g.DrawString("БЫЛО",font,Brushes.White,20,12);g.DrawString("СТАЛО · 16:9",font,Brushes.White,750,12);
                for(int n=0;n<3;n++) {
                    int index=page*3+n;string race=Races[index];int y=65+n*584;
                    g.DrawString(Titles[index],label,Brushes.Gainsboro,20,y);
                    using(var a=Preview(race,false,screenshot))using(var b=Preview(race,true,screenshot)) {
                        a.Save(Path.Combine(Root,"previews",race+"-before.png"),ImageFormat.Png);
                        b.Save(Path.Combine(Root,"previews",race+"-after.png"),ImageFormat.Png);
                        g.DrawImageUnscaled(a,10,y+30);g.DrawImageUnscaled(b,740,y+30);
                    }
                }
                g.DrawString("Предпросмотр файлов интерфейса. Изображение карты взято с твоего скриншота; игру не запускал.",label,Brushes.Silver,20,1815);
                sheet.Save(Path.Combine(Root,"previews","comparison-"+(page+1)+".png"),ImageFormat.Png);
            }
        }
    }
    public static int Main(string[] args)
    {
        try {
            Root=Path.GetFullPath(args[0]);Aspect=double.Parse(args[1],CultureInfo.InvariantCulture);
            if(Aspect<1.34||Aspect>3.6)throw new Exception("This local asset fitter is for widescreen displays");
            Directory.CreateDirectory(Path.Combine(Root,"previews"));
            bool observer=args.Length>2&&args[2]=="--observer";
            foreach(string race in observer?new[]{"Observer"}:Races)foreach(string variant in Variants)Build(race,variant);
            File.WriteAllText(Path.Combine(Root,"assets.tsv"),"path\twidth\theight\tchangedPixels\tsourceSha256\tsha256\n"+string.Join("\n",Rows)+"\n",new UTF8Encoding(false));
            if(!observer)Previews(args[2]);return 0;
        } catch(Exception e){Console.Error.WriteLine(e);return 1;}
    }
}
