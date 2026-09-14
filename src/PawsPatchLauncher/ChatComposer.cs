using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;

namespace PawsPatchLauncher;

// Wire format is plain text with explicit :ch_*: tokens, never RTF/HTML or control characters.
public sealed class ChatComposer : RichTextBox
{
    private bool _changing;
    private long _editRevision;
    public int MaxLength { get; set; } = 2000;
    public string UiLanguage { get; set; } = "en";
    public bool Russian { get => UiLanguage == "ru"; set => UiLanguage = value ? "ru" : "en"; }
    public Func<string, Task<bool>>? CopyTextRequested { get; set; }

    public ChatComposer()
    {
        Document = new FlowDocument(new Paragraph { Margin = new(0) }) { PagePadding = new(0) };
        IsDocumentEnabled = false;
        ContextMenu = new ContextMenu();
        ContextMenuOpening += (_, _) =>
        {
            ContextMenu.Items.Clear();
            if (TryFindResource("SocialContextMenu") is Style menuStyle) ContextMenu.Style = menuStyle;
            foreach (var (ru, en, command) in new[] {
                ("Отменить", "Undo", ApplicationCommands.Undo), ("Повторить", "Redo", ApplicationCommands.Redo),
                ("Вырезать", "Cut", ApplicationCommands.Cut), ("Копировать", "Copy", ApplicationCommands.Copy),
                ("Вставить", "Paste", ApplicationCommands.Paste), ("Выделить всё", "Select all", ApplicationCommands.SelectAll) })
            {
                var item = new MenuItem { Header = UiLanguages.Text(UiLanguage,ru,en), Command = command, CommandTarget = this, InputGestureText = "" };
                if (TryFindResource("SocialMenuItem") is Style style) item.Style = style;
                item.Click += (_, _) => ActionJournal.Record("chat.edit", command.Name);
                ContextMenu.Items.Add(item);
            }
        };
        DataObject.AddPastingHandler(this, (_, e) =>
        {
            e.CancelCommand();
            if (e.DataObject.GetData(DataFormats.UnicodeText) is string text) InsertText(text);
        });
        CommandBindings.Add(new CommandBinding(ApplicationCommands.Copy, async (_, e) =>
        {
            e.Handled = true; await CopySelectionAsync(false);
        }));
        CommandBindings.Add(new CommandBinding(ApplicationCommands.Cut, async (_, e) =>
        {
            e.Handled = true; await CopySelectionAsync(true);
        }));
    }

    public string Text
    {
        get => Serialize(Document.ContentStart, Document.ContentEnd);
        set
        {
            _changing = true;
            try
            {
                Document.Blocks.Clear();
                var paragraph = new Paragraph { Margin = new(0) };
                paragraph.Inlines.AddRange(ChatGlyphs.Inlines(value[..Math.Min(value.Length, MaxLength)], UiLanguage));
                Document.Blocks.Add(paragraph);
            }
            finally { _changing = false; }
        }
    }

    public void Clear() { Text = ""; }
    private async Task CopySelectionAsync(bool cut)
    {
        if (Selection.IsEmpty || CopyTextRequested is null) return;
        var revision = _editRevision; var start = Selection.Start; var end = Selection.End;
        var text = Serialize(start, end);
        if (await CopyTextRequested(text) && cut && revision == _editRevision
            && start.CompareTo(Selection.Start) == 0 && end.CompareTo(Selection.End) == 0) Selection.Text = "";
    }
    public void InsertGlyph(ChatGlyph glyph) => InsertText(glyph.Token);

    public void InsertText(string text)
    {
        text = text.Replace("\r\n", "\n").Replace('\r', '\n');
        var room = MaxLength - Text.Length + Serialize(Selection.Start, Selection.End).Length;
        if (text.Length > room) return;
        BeginChange();
        try
        {
            Selection.Text = "";
            var position = CaretPosition.GetInsertionPosition(LogicalDirection.Forward);
            if (position.Paragraph is null)
            {
                var paragraph = new Paragraph { Margin = new(0) }; Document.Blocks.Add(paragraph); position = paragraph.ContentStart;
            }
            foreach (var inline in ChatGlyphs.Inlines(text, UiLanguage))
            {
                Inline inserted;
                if (inline is InlineUIContainer icon)
                {
                    var child = icon.Child; icon.Child = null;
                    inserted = new InlineUIContainer(child, position) { Tag = icon.Tag, BaselineAlignment = BaselineAlignment.Center };
                }
                else inserted = new Run(((Run)inline).Text, position);
                position = inserted.ElementEnd;
            }
            CaretPosition = position;
        }
        finally { EndChange(); }
        Focus();
    }

    protected override void OnPreviewTextInput(TextCompositionEventArgs e)
    {
        if (Text.Length - Serialize(Selection.Start, Selection.End).Length + e.Text.Length > MaxLength) e.Handled = true;
        base.OnPreviewTextInput(e);
    }

    protected override void OnTextChanged(TextChangedEventArgs e)
    {
        _editRevision++;
        if (!_changing && Text.Length > MaxLength && CanUndo)
        {
            _changing = true;
            try { Undo(); } finally { _changing = false; }
        }
        base.OnTextChanged(e);
    }

    private static string Serialize(TextPointer start, TextPointer end)
    {
        var text = new StringBuilder(); var p = start;
        while (p.CompareTo(end) < 0)
        {
            var context = p.GetPointerContext(LogicalDirection.Forward);
            if (context == TextPointerContext.Text)
            {
                var run = p.GetTextInRun(LogicalDirection.Forward);
                var length = Math.Min(run.Length, p.GetOffsetToPosition(end));
                text.Append(run.AsSpan(0, length)); p = p.GetPositionAtOffset(length)!; continue;
            }
            if (context == TextPointerContext.ElementStart && p.GetAdjacentElement(LogicalDirection.Forward) is InlineUIContainer icon && icon.Tag is string token)
            { text.Append(token); p = icon.ElementEnd; continue; }
            if (context == TextPointerContext.ElementStart && p.GetAdjacentElement(LogicalDirection.Forward) is LineBreak) text.Append('\n');
            if (context == TextPointerContext.ElementEnd && p.GetAdjacentElement(LogicalDirection.Forward) is Paragraph { NextBlock: not null }) text.Append('\n');
            p = p.GetNextContextPosition(LogicalDirection.Forward) ?? end;
        }
        return text.ToString();
    }
}
