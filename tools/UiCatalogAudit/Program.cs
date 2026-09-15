using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using System.Text.Json;
using System.Text.RegularExpressions;

var root=Path.GetFullPath(args[0]);var output=Path.GetFullPath(args[1]);
var pairs=new SortedDictionary<string,string>(StringComparer.Ordinal);
var locations=new Dictionary<string,HashSet<string>>();
string? Text(ExpressionSyntax e) => e switch {
    LiteralExpressionSyntax l when l.IsKind(SyntaxKind.StringLiteralExpression)=>l.Token.ValueText,
    BinaryExpressionSyntax b when b.IsKind(SyntaxKind.AddExpression) && Text(b.Left) is string left && Text(b.Right) is string right=>left+right,
    InterpolatedStringExpressionSyntax s=>Interpolated(s), _=>null};
string Interpolated(InterpolatedStringExpressionSyntax s)
{
    int index=0;
    return string.Concat(s.Contents.Select(n=>n is InterpolatedStringTextSyntax t?t.TextToken.ValueText:
        n is InterpolationSyntax i?"{"+(index++)+(i.AlignmentClause is {} a?","+a.Value.ToString():"")+(i.FormatClause is {} f?":"+f.FormatStringToken.ValueText:"")+"}":""));
}
void Add(string? ru,string? en,string path)
{
    if(ru is null||en is null||!Regex.IsMatch(ru,"[А-Яа-яЁё]")||!Regex.IsMatch(en,"[A-Za-z]"))return;
    pairs.TryAdd(en,ru);if(!locations.ContainsKey(en))locations[en]=new();locations[en].Add(Path.GetRelativePath(root,path));
}
foreach(var path in Directory.EnumerateFiles(root,"*.cs",SearchOption.AllDirectories).Where(p=>!p.Contains(Path.DirectorySeparatorChar+"obj"+Path.DirectorySeparatorChar)&&!p.Contains(Path.DirectorySeparatorChar+"bin"+Path.DirectorySeparatorChar)))
{
    var tree=CSharpSyntaxTree.ParseText(File.ReadAllText(path));var syntax=tree.GetRoot();
    foreach(var call in syntax.DescendantNodes().OfType<InvocationExpressionSyntax>())
    {
        var name=call.Expression is MemberAccessExpressionSyntax member?member.Name.Identifier.ValueText:call.Expression.ToString();
        var a=call.ArgumentList.Arguments;
        if((name=="T"||name=="TF")&&a.Count==2)Add(Text(a[0].Expression),Text(a[1].Expression),path);
        if((name=="Text"||name=="Format")&&call.Expression.ToString().StartsWith("UiLanguages.")&&a.Count==3)Add(Text(a[1].Expression),Text(a[2].Expression),path);
    }
    foreach(var tuple in syntax.DescendantNodes().OfType<TupleExpressionSyntax>().Where(t=>t.Arguments.Count==2))Add(Text(tuple.Arguments[0].Expression),Text(tuple.Arguments[1].Expression),path);
    foreach(var arguments in syntax.DescendantNodes().OfType<ArgumentListSyntax>())
        for(int i=0;i+1<arguments.Arguments.Count;i++)Add(Text(arguments.Arguments[i].Expression),Text(arguments.Arguments[i+1].Expression),path);
    foreach(var initializer in syntax.DescendantNodes().OfType<InitializerExpressionSyntax>())
    {
        var assignments=initializer.Expressions.OfType<AssignmentExpressionSyntax>().ToArray();
        var ru=assignments.FirstOrDefault(x=>x.Left.ToString()=="Ru")?.Right;
        var en=assignments.FirstOrDefault(x=>x.Left.ToString()=="En")?.Right;
        if(ru is not null&&en is not null)Add(Text(ru),Text(en),path);
    }
    var vars=syntax.DescendantNodes().OfType<VariableDeclaratorSyntax>().Where(v=>v.Initializer!=null).GroupBy(v=>v.Identifier.ValueText).ToDictionary(g=>g.Key,g=>g.First().Initializer!.Value);
    foreach(var (name,e) in vars.Where(p=>p.Key.EndsWith("Ru")))if(vars.TryGetValue(name[..^2]+"En",out var en))Add(Text(e),Text(en),path);
}
Directory.CreateDirectory(Path.GetDirectoryName(output)!);
File.WriteAllText(output,JsonSerializer.Serialize(new{pairs,locations},new JsonSerializerOptions{WriteIndented=true,Encoder=System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping}));
Console.WriteLine($"AUTHORED UI PAIRS {pairs.Count}");
