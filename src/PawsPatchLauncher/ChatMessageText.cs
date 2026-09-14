using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;

namespace PawsPatchLauncher;

public sealed class ChatMessageText : RichTextBox
{
    public string UiLanguage { get; set; } = "en";
    public Func<string,Task<bool>>? CopyTextRequested { get; set; }
    public string Text
    {
        get => ChatComposer.Serialize(Document.ContentStart,Document.ContentEnd);
        set
        {
            var paragraph=new Paragraph {Margin=new(0)};
            paragraph.Inlines.AddRange(ChatGlyphs.Inlines(value,UiLanguage));
            Document=new FlowDocument(paragraph) {PagePadding=new(0)};
        }
    }
    public string SelectedText => ChatComposer.Serialize(Selection.Start,Selection.End);
    public ChatMessageText()
    {
        Style=new Style(typeof(RichTextBox));
        IsReadOnly=true; IsReadOnlyCaretVisible=false; IsUndoEnabled=false; IsDocumentEnabled=false;
        IsInactiveSelectionHighlightEnabled=true;
        BorderThickness=new(0); Padding=new(0); Background=Brushes.Transparent; FocusVisualStyle=null;
        HorizontalScrollBarVisibility=ScrollBarVisibility.Disabled; VerticalScrollBarVisibility=ScrollBarVisibility.Disabled;
        SelectionBrush=new SolidColorBrush(Color.FromRgb(91,134,179)); SelectionOpacity=.65;
        Text="";
        CommandBindings.Add(new CommandBinding(ApplicationCommands.Copy,async (_,e)=>
        {
            e.Handled=true;
            if(!Selection.IsEmpty && CopyTextRequested is { } copy)await copy(SelectedText);
        },(_,e)=>{e.CanExecute=!Selection.IsEmpty;e.Handled=true;}));
        ContextMenu=new ContextMenu();
        ContextMenuOpening+=(_,_)=>
        {
            ContextMenu.Items.Clear();
            if(TryFindResource("SocialContextMenu") is Style menuStyle)ContextMenu.Style=menuStyle;
            foreach(var (ru,en,command) in new[]{("Копировать","Copy",ApplicationCommands.Copy),("Выделить всё","Select all",ApplicationCommands.SelectAll)})
            {
                var item=new MenuItem {Header=UiLanguages.Text(UiLanguage,ru,en),Command=command,CommandTarget=this,InputGestureText=""};
                if(TryFindResource("SocialMenuItem") is Style itemStyle)item.Style=itemStyle;
                ContextMenu.Items.Add(item);
            }
        };
    }
}
