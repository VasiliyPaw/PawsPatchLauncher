using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

// Owned local companion window: no simulation writes, game input hooks or web UI.
internal sealed class CitySettingsForm : Form
{
    internal sealed class BranchOption
    {
        internal string Family, Source, Target, Name, Effects;
    }
    internal sealed class View
    {
        internal uint Epoch;
        internal float[] Income;
        internal string Status;
        internal Dictionary<uint,string> Cities=new Dictionary<uint,string>();
        internal BranchOption[] Options=new BranchOption[0];
    }
    internal CityPolicy Result;
    private readonly bool ru;
    private readonly CityPolicy draft;
    private readonly View view;
    private readonly Color background=Color.FromArgb(12,25,40), card=Color.FromArgb(23,44,65), gold=Color.FromArgb(219,178,84);
    private readonly FlowLayoutPanel body=new FlowLayoutPanel();
    private readonly List<Button> tabs=new List<Button>();
    private int currentTab;
    private string T(string r,string e) { return ru?r:e; }
    internal static string ResourceName(int i,bool russian)
    {
        string[] r={"Золото","Камень","Дерево","Железо","Мана"},e={"Gold","Stone","Wood","Iron","Mana"};
        return i<5?(russian?r[i]:e[i]):i.ToString();
    }
    internal static string DeltaText(float[] delta,bool russian)
    {
        // Catalog entries outlive the snapshot that discovered a branch. Show
        // its net effect, not an obsolete kingdom-wide before/after balance.
        string text=string.Join(" · ",Enumerable.Range(0,Math.Min(5,delta.Length))
            .Where(i=>Math.Abs(delta[i])>.0001f)
            .Select(i=>ResourceName(i,russian)+" "+delta[i].ToString("+0.##;-0.##;0")).ToArray());
        return text.Length>0?text:(russian?"Доход ресурсов не изменится.":"Resource income is unchanged.");
    }
    internal CitySettingsForm(CityPolicy policy,View state,bool russian)
    {
        draft=policy.Copy();view=state;ru=russian;
        Text=T("Автоулучшение городов — Paw’s Patch","City Auto-Upgrade — Paw’s Patch");
        Font=new Font("Segoe UI",10);BackColor=background;ForeColor=Color.WhiteSmoke;
        ClientSize=new Size(770,600);MinimumSize=new Size(720,550);StartPosition=FormStartPosition.CenterScreen;
        MaximizeBox=false;MinimizeBox=false;ShowInTaskbar=true;Cursor=Cursors.Default;
        var layout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=5,Padding=new Padding(20)};
        foreach(int h in new[]{44,44,34}) layout.RowStyles.Add(new RowStyle(SizeType.Absolute,h));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,56));
        Controls.Add(layout);
        layout.Controls.Add(new Label {Text=T("Автоулучшение городов","City Auto-Upgrade"),Font=new Font(Font.FontFamily,17,FontStyle.Bold),Dock=DockStyle.Fill},0,0);
        var nav=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false};layout.Controls.Add(nav,0,1);
        string[] names={T("Общее","General"),T("Ветки","Upgrade Paths"),T("Города","Cities")};
        for(int i=0;i<names.Length;i++) {int tab=i;var button=Button(names[i],115);button.Click+=delegate {ShowTab(tab);};nav.Controls.Add(button);tabs.Add(button);}
        layout.Controls.Add(new Label {Text=T("Новые автоматические приказы приостановлены до закрытия окна.","New automatic orders are paused until this window closes."),ForeColor=gold,Dock=DockStyle.Fill},0,2);
        body.Dock=DockStyle.Fill;body.AutoScroll=true;body.WrapContents=false;body.FlowDirection=FlowDirection.TopDown;body.Padding=new Padding(0,5,8,0);
        body.SizeChanged+=delegate {foreach(Control c in body.Controls)c.Width=Math.Max(300,body.ClientSize.Width-28);};layout.Controls.Add(body,0,3);
        var footer=new FlowLayoutPanel {Dock=DockStyle.Fill,FlowDirection=FlowDirection.RightToLeft,Padding=new Padding(0,12,0,0)};
        var apply=Button(T("Применить","Apply"),135);apply.BackColor=Color.FromArgb(37,111,77);apply.Click+=delegate {Result=draft;DialogResult=DialogResult.OK;Close();};
        var cancel=Button(T("Отмена","Cancel"),115);cancel.Click+=delegate {DialogResult=DialogResult.Cancel;Close();};CancelButton=cancel;
        footer.Controls.Add(apply);footer.Controls.Add(cancel);layout.Controls.Add(footer,0,4);ShowTab(0);
    }
    private Button Button(string text,int width)
    {
        var b=new Button {Text=text,Width=width,Height=34,FlatStyle=FlatStyle.Flat,BackColor=card,ForeColor=ForeColor,Margin=new Padding(0,0,8,6),UseVisualStyleBackColor=false};
        b.FlatAppearance.BorderColor=Color.FromArgb(62,86,107);b.FlatAppearance.MouseOverBackColor=Color.FromArgb(40,67,91);return b;
    }
    private Panel Row(int height)
    { var p=new Panel {Height=height,Width=Math.Max(300,body.ClientSize.Width-28),BackColor=card,Margin=new Padding(0,0,0,10),Padding=new Padding(12)};body.Controls.Add(p);return p; }
    private void Note(string text,int height)
    {var p=Row(height);p.Controls.Add(new Label {Text=text,Dock=DockStyle.Fill,ForeColor=Color.FromArgb(183,204,223)});}
    private void Toggle(string text,bool value,Action<bool> changed)
    {var p=Row(48);var c=new CheckBox {Text=text,Checked=value,Dock=DockStyle.Fill,AutoSize=false};c.CheckedChanged+=delegate {changed(c.Checked);};p.Controls.Add(c);}
    private void ShowTab(int tab)
    {
        currentTab=tab;body.SuspendLayout();foreach(Control c in body.Controls.Cast<Control>().ToArray())c.Dispose();body.Controls.Clear();
        for(int i=0;i<tabs.Count;i++) tabs[i].BackColor=i==tab?Color.FromArgb(89,70,28):card;
        if(tab==0)
        {
            Note(T("Защита ресурсов всегда включена\nНельзя создать новый дефицит или усилить существующий — даже ради золота.","Resource protection is always on\nNever create or worsen a deficit, even for additional gold."),76);
            Toggle(T("Строить новые здания","Construct new buildings"),draft.AllowNew,v=>draft.AllowNew=v);
            Toggle(T("Улучшать существующие здания","Upgrade existing buildings"),draft.AllowUpgrade,v=>draft.AllowUpgrade=v);
            Toggle(T("Разрешить улучшения без изменения дохода","Allow upgrades with unchanged income"),draft.AllowOther,v=>draft.AllowOther=v);
            Note(T("Приоритет: пороги ресурсов → золото → новые здания и центр города → ресурсы для следующей золотой ветки.\nПороги дохода и запас золота задаются в панели F1.","Priority: resource targets → gold → new buildings and city center → resources for the next gold upgrade.\nSet income targets and the gold reserve in the F1 panel."),80);
            Note(view.Status??"",75);
        }
        else if(tab==1) Branches(0);
        else
        {
            Note(T("Исключённый город остаётся полностью под ручным управлением. Исключения и местные ветки действуют только в текущем матче и сбрасываются при загрузке сохранения.","Excluded cities stay under manual control. City exceptions and local branches apply only to this match and reset when loading a save."),80);
            foreach(var city in view.Cities.OrderBy(c=>c.Value))
            {uint id=city.Key;Toggle(city.Value+T(" — автоулучшение"," — auto-upgrade"),!draft.Excluded.Contains(id),v=>{if(v)draft.Excluded.Remove(id);else draft.Excluded.Add(id);});}
        }
        body.ResumeLayout();
    }
    private sealed class Choice {internal string Key,Title;public override string ToString(){return Title;}}
    private ComboBox Combo() { return new ComboBox {DropDownStyle=ComboBoxStyle.DropDownList,BackColor=background,ForeColor=Color.White,FlatStyle=FlatStyle.Flat,Height=30}; }
    private void Branches(uint city)
    {
        var scope=Row(52);var select=Combo();select.Dock=DockStyle.Fill;select.Items.Add(new Choice {Key="0",Title=T("Общие правила для всех городов","Global rules for all cities")});
        foreach(var c in view.Cities.OrderBy(x=>x.Value)) select.Items.Add(new Choice {Key=c.Key.ToString(),Title=c.Value});
        select.SelectedIndex=select.Items.Cast<Choice>().ToList().FindIndex(c=>c.Key==city.ToString());scope.Controls.Add(select);
        select.SelectedIndexChanged+=delegate {uint id=uint.Parse(((Choice)select.SelectedItem).Key);foreach(Control c in body.Controls.Cast<Control>().ToArray())c.Dispose();body.Controls.Clear();Branches(id);};
        Note(T("Правило относится к переходу из указанного здания. «Вручную» останавливает выбор развилки, но разрешает линейное улучшение. Недоступная выбранная ветка не заменяется другой.","Rules apply to upgrades from the listed building. Manual stops at forks but allows linear upgrades. An unavailable chosen branch is never replaced."),85);
        var groups=view.Options.GroupBy(o=>o.Family).OrderBy(g=>g.First().Source).ToArray();
        if(groups.Length==0) Note(T("Ветки появятся, когда в ваших городах будут здания с улучшениями.","Branches appear when your cities contain upgradeable buildings."),65);
        foreach(var group in groups)
        {
            string family=group.Key;var row=Row(122);var title=new Label {Text=group.First().Source,Left=12,Top=9,Width=580,Height=23,ForeColor=gold};row.Controls.Add(title);
            var choice=Combo();choice.Left=12;choice.Top=38;choice.Width=row.Width-24;choice.Anchor=AnchorStyles.Left|AnchorStyles.Right|AnchorStyles.Top;
            if(city!=0)choice.Items.Add(new Choice {Key="inherit",Title=T("Как в общих правилах","Use global rule")});
            choice.Items.Add(new Choice {Key="auto",Title=T("Автоматически — безопасный вариант","Automatic — safe choice")});
            choice.Items.Add(new Choice {Key="manual",Title=T("Выбирать развилки вручную","Choose branches manually")});
            foreach(var o in group.GroupBy(o=>o.Target).Select(g=>g.First()).OrderBy(o=>o.Name))choice.Items.Add(new Choice {Key=o.Target,Title=o.Name});
            string rule="inherit";Dictionary<string,string> local;
            if(city==0)rule=draft.Rule(0,family);else if(draft.CityBranches.TryGetValue(city,out local))local.TryGetValue(family,out rule);
            if(string.IsNullOrEmpty(rule))rule="inherit";
            int index=choice.Items.Cast<Choice>().ToList().FindIndex(c=>c.Key==rule);
            if(index<0) {choice.Items.Add(new Choice {Key=rule,Title=T("Выбранная ветка сейчас недоступна","Selected branch is currently unavailable")});index=choice.Items.Count-1;}
            choice.SelectedIndex=index;
            var effects=new Label {Left=12,Top=76,Width=row.Width-24,Height=37,Anchor=AnchorStyles.Left|AnchorStyles.Right|AnchorStyles.Top,ForeColor=Color.FromArgb(183,204,223)};
            Action refresh=delegate {var o=group.FirstOrDefault(v=>v.Target==((Choice)choice.SelectedItem).Key);effects.Text=o==null?T("Защита баланса ресурсов действует при любом выборе.","Resource balance protection applies to every choice."):o.Effects;};
            choice.SelectedIndexChanged+=delegate
            {
                string key=((Choice)choice.SelectedItem).Key;
                if(city==0) draft.Branches[family]=key;
                else {Dictionary<string,string> map;if(!draft.CityBranches.TryGetValue(city,out map))draft.CityBranches[city]=map=new Dictionary<string,string>();if(key=="inherit")map.Remove(family);else map[family]=key;}
                refresh();
            };
            row.Controls.Add(choice);row.Controls.Add(effects);refresh();
        }
    }
}
