using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;

namespace PawsPatchLauncher;

public sealed class ChatMessageText : RichTextBox
{
    private bool _clampingSelection;
    private SelectionOwner? _selectionOwner;
    private static readonly DependencyProperty SelectionOwnerProperty = DependencyProperty.RegisterAttached(
        "SelectionOwner", typeof(SelectionOwner), typeof(ChatMessageText));
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
        IsInactiveSelectionHighlightEnabled=false;
        BorderThickness=new(0); Padding=new(0); Background=Brushes.Transparent; FocusVisualStyle=null;
        HorizontalScrollBarVisibility=ScrollBarVisibility.Disabled; VerticalScrollBarVisibility=ScrollBarVisibility.Disabled;
        SelectionBrush=new SolidColorBrush(Color.FromRgb(91,134,179)); SelectionOpacity=.65;
        Text="";
        Unloaded+=(_,_)=>ClearSelection();
        IsVisibleChanged+=(_,_)=>{if(!IsVisible)ClearSelection();};
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

    protected override void OnSelectionChanged(RoutedEventArgs e)
    {
        if (_clampingSelection) return;
        // The document's final paragraph marker is not part of a sent message.
        // Selecting it paints an extra empty cell after the final character.
        if (Document.Blocks.FirstBlock is { } first && Document.Blocks.LastBlock is { } last)
        {
            var start = Selection.Start.CompareTo(first.ContentStart) < 0 ? first.ContentStart : Selection.Start;
            var end = Selection.End.CompareTo(last.ContentEnd) > 0 ? last.ContentEnd : Selection.End;
            if (start.CompareTo(last.ContentEnd) > 0) start = last.ContentEnd;
            if (end.CompareTo(first.ContentStart) < 0) end = first.ContentStart;
            if (start.CompareTo(Selection.Start) != 0 || end.CompareTo(Selection.End) != 0)
            {
                var backwards = CaretPosition.CompareTo(Selection.Start) == 0;
                _clampingSelection = true;
                try { Selection.Select(backwards ? end : start, backwards ? start : end); }
                finally { _clampingSelection = false; }
            }
        }
        base.OnSelectionChanged(e);
        if (Selection.IsEmpty) _selectionOwner?.Forget(this);
        else if (Window.GetWindow(this) is { } window)
        {
            var owner = window.GetValue(SelectionOwnerProperty) as SelectionOwner;
            if (owner is null) window.SetValue(SelectionOwnerProperty, owner = new SelectionOwner(window));
            _selectionOwner = owner;
            owner.Select(this);
        }
    }

    private void ClearSelection()
    {
        if (!Selection.IsEmpty) Selection.Select(Selection.Start, Selection.Start);
        _selectionOwner?.Forget(this);
        _selectionOwner = null;
    }

    private sealed class SelectionOwner
    {
        private ChatMessageText? _selected;
        public SelectionOwner(Window window)
        {
            // Observe even handled clicks on non-focusable backgrounds/overlays;
            // do not consume the click or change normal button/menu behavior.
            window.AddHandler(Mouse.PreviewMouseDownEvent, new MouseButtonEventHandler((_, e) =>
            {
                if (!InsideSelection(e.OriginalSource as DependencyObject)) Clear();
            }), true);
            window.AddHandler(Keyboard.GotKeyboardFocusEvent, new KeyboardFocusChangedEventHandler((_, e) =>
            {
                if (!InsideSelection(e.NewFocus as DependencyObject)) Clear();
            }), true);
            window.Deactivated += (_, _) => Clear();
            window.Closed += (_, _) => Clear();
        }
        public void Select(ChatMessageText message)
        {
            if (ReferenceEquals(_selected, message)) return;
            Clear();
            _selected = message;
        }
        public void Forget(ChatMessageText message)
        {
            if (ReferenceEquals(_selected, message)) _selected = null;
        }
        private void Clear()
        {
            var previous = _selected;
            _selected = null;
            previous?.ClearSelection();
        }
        private bool InsideSelection(DependencyObject? source)
        {
            for (var node = source; node is not null;)
            {
                if (ReferenceEquals(node, _selected) ||
                    _selected?.ContextMenu is { IsOpen: true } menu && ReferenceEquals(node, menu)) return true;
                node = node is Visual or System.Windows.Media.Media3D.Visual3D ? VisualTreeHelper.GetParent(node)
                    : node is FrameworkContentElement content ? content.Parent : LogicalTreeHelper.GetParent(node);
            }
            return false;
        }
    }
}
