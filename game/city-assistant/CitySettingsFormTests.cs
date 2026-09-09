using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;

// Offline component tests only: never attach to or send input to the game.
internal static class CitySettingsFormTests
{
    private static int checks;
    private static void Check(bool ok,string name) { if(!ok) throw new Exception(name);checks++; }
    private static IEnumerable<Control> All(Control c)
    { yield return c;foreach(Control child in c.Controls)foreach(Control nested in All(child))yield return nested; }
    [STAThread]
    private static int Main()
    {
        Check(CitySettingsForm.DeltaText(new float[]{24,0,0,-2,0},false)=="Gold +24 · Iron -2","net branch effects");
        Check(CitySettingsForm.DeltaText(new float[]{0,0,0,6,0},false)=="Iron +6","no stale kingdom balance");
        Check(CitySettingsForm.DeltaText(new float[]{0,0,0,0,0,1},false)=="Resource income is unchanged.","bookkeeping excluded");
        foreach(bool ru in new[]{false,true})
        {
            var policy=new CityPolicy();policy.Floors[3]=2;
            var view=new CitySettingsForm.View {Epoch=1,Income=new float[]{18,0,0,6,0}};
            view.Cities.Add(1,"Bluewater Springs");
            view.Options=new[]{new CitySettingsForm.BranchOption {Family="forge",Source="Blacksmith",Target="iron",Name="Ironworks",Effects=CitySettingsForm.DeltaText(new float[]{0,0,0,6,0},ru)}};
            using(var form=new CitySettingsForm(policy,view,ru))
            {
                var tab=typeof(CitySettingsForm).GetMethod("ShowTab",BindingFlags.NonPublic|BindingFlags.Instance);
                for(int page=0;page<3;page++)
                {
                    tab.Invoke(form,new object[]{page});
                    Control[] controls=All(form).ToArray();
                    Check(controls.Length>6,"page populated");
                    if(!ru)Check(controls.All(c=>!c.Text.Any(ch=>ch>='\u0400'&&ch<='\u04ff')),"English has no hardcoded Russian");
                    Check(!controls.OfType<NumericUpDown>().Any(),"income targets moved to F1");
                    Check(!controls.OfType<Button>().Any(c=>c.Text=="Resources" || c.Text=="Ресурсы"),"no duplicate resource tab");
                    Check(policy.Floors[3]==2,"existing income target preserved");
                    if(page==1)
                    {
                        var combos=controls.OfType<ComboBox>().ToArray();
                        Check(combos.Length==2,"scope and branch controls");
                        Check(combos[1].Items.Cast<object>().Any(x=>x.ToString()=="Ironworks"),"real branch label");
                        combos[1].SelectedIndex=2;
                        Check(All(form).Any(c=>c.Text==view.Options[0].Effects),"branch effect displayed");
                        combos[0].SelectedIndex=1;
                        Check(All(form).OfType<ComboBox>().Last().Items.Count==4,"city inheritance option");
                        Check(policy.Branches.Count==0,"branch draft isolated");
                    }
                    if(page==2)Check(controls.OfType<CheckBox>().Single().Text.Contains("Bluewater Springs"),"city name");
                }
                Check(form.Result==null,"unapplied form has no result");
            }
        }
        Console.WriteLine("CITY_SETTINGS_FORM_PASS "+checks+" checks; no game or windows opened");return 0;
    }
}
