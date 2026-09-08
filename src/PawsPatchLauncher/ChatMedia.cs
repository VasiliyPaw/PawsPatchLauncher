using System.Buffers.Binary;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

// External media never enters Supabase, disk caches, logs, or authenticated HTTP clients.
public sealed class ChatMedia : IDisposable
{
    public const int MaximumBytes=8*1024*1024;
    private readonly HttpClient _http;
    private readonly SemaphoreSlim _slots=new(2);
    private readonly Dictionary<string,byte[]> _cache=[];
    private long _cacheBytes;
    private bool _disposed;
    public ChatMedia(HttpMessageHandler? transport=null)
    {
        var handler=transport??new SocketsHttpHandler{AllowAutoRedirect=false,UseCookies=false,UseProxy=false,AutomaticDecompression=DecompressionMethods.None,
            ConnectCallback=ConnectPublicAsync,MaxConnectionsPerServer=2,ConnectTimeout=TimeSpan.FromSeconds(8)};
        _http=new HttpClient(handler){Timeout=TimeSpan.FromSeconds(20)};
    }
    public static bool IsPublic(IPAddress ip)
    {
        if(ip.IsIPv4MappedToIPv6)ip=ip.MapToIPv4();
        if(IPAddress.IsLoopback(ip))return false;
        var b=ip.GetAddressBytes();
        if(b.Length==16)return (b[0]&0xe0)==0x20 && !(b[0]==0x20&&b[1]==2)
            && !(b[0]==0x20&&b[1]==1&&(b[2]<2||b[2]==0x0d&&b[3]==0xb8));
        return b[0] is not (0 or 10 or 127) && b[0]<224 && !(b[0]==169&&b[1]==254)
            && !(b[0]==172&&b[1]>=16&&b[1]<=31) && !(b[0]==192&&(b[1]==168||b[1]==0||b[1]==2))
            && !(b[0]==100&&b[1]>=64&&b[1]<=127) && !(b[0]==198&&(b[1] is 18 or 19||b[1]==51&&b[2]==100))
            && !(b[0]==203&&b[1]==0&&b[2]==113);
    }
    private static async ValueTask<Stream> ConnectPublicAsync(SocketsHttpConnectionContext context,CancellationToken ct)
    {
        // Validate the addresses actually used to connect, not a separate preflight DNS answer.
        var addresses=await Dns.GetHostAddressesAsync(context.DnsEndPoint.Host,ct);
        if(addresses.Length==0||addresses.Any(ip=>!IsPublic(ip)))throw new HttpRequestException("Non-public media host.");
        foreach(var ip in addresses){
            var socket=new Socket(ip.AddressFamily,SocketType.Stream,ProtocolType.Tcp);
            try{await socket.ConnectAsync(new IPEndPoint(ip,context.DnsEndPoint.Port),ct);return new NetworkStream(socket,true);}
            catch{socket.Dispose();if(ct.IsCancellationRequested)throw;}
        }
        throw new HttpRequestException("Media connection failed.");
    }
    public static bool Allowed(Uri uri)=>uri.IsAbsoluteUri&&uri.Scheme=="https"&&uri.Port==443&&uri.UserInfo.Length==0
        &&uri.OriginalString.Length<=4096&&uri.Host.Contains('.')&&uri.HostNameType!=UriHostNameType.Unknown
        &&(!IPAddress.TryParse(uri.Host,out var ip)||IsPublic(ip));
    public static bool Automatic(Uri uri)=>new[]{"media.discordapp.net","cdn.discordapp.com","media.tenor.com","i.imgur.com","media.giphy.com","i.giphy.com"}.Contains(uri.IdnHost,StringComparer.OrdinalIgnoreCase);
    public static IReadOnlyList<Uri> Find(string text)
    {
        return Regex.Matches(text,@"https://[^\s<>""']+",RegexOptions.IgnoreCase,TimeSpan.FromMilliseconds(50))
            .Cast<Match>().Select(m=>Uri.TryCreate(m.Value.TrimEnd(')',']',',','.'),UriKind.Absolute,out var u)?u:null)
            .Where(u=>u is not null&&Allowed(u)&&new[]{".png",".jpg",".jpeg",".gif"}.Contains(Path.GetExtension(u.AbsolutePath).ToLowerInvariant()))
            .Select(u=>u!).Distinct().Take(2).ToArray();
    }
    public static string WithoutLoadedLinks(string body,IReadOnlySet<string> loaded)
    {
        if(loaded.Count==0)return body;
        return Regex.Replace(body,@"https://[^\s<>""']+",match=>{
            var token=match.Value.TrimEnd(')',']',',','.');
            return Uri.TryCreate(token,UriKind.Absolute,out var uri)&&loaded.Contains(uri.AbsoluteUri)
                ?match.Value[token.Length..]:match.Value;
        },RegexOptions.IgnoreCase,TimeSpan.FromMilliseconds(50)).Trim();
    }
    public async Task<byte[]> LoadAsync(Uri uri,CancellationToken ct)
    {
        if(!Allowed(uri))throw new InvalidDataException();
        lock(_cache){if(_cache.TryGetValue(uri.AbsoluteUri,out var found))return found;}
        await _slots.WaitAsync(ct);
        try{
            ObjectDisposedException.ThrowIf(_disposed,this);
            using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(TimeSpan.FromSeconds(20));
            var current=uri;
            for(int redirect=0;redirect<4;redirect++){
                using var response=await _http.GetAsync(current,HttpCompletionOption.ResponseHeadersRead,timeout.Token);
                if((int)response.StatusCode is >=300 and <400){
                    var location=response.Headers.Location??throw new InvalidDataException();
                    current=location.IsAbsoluteUri?location:new Uri(current,location);
                    if(!Allowed(current))throw new InvalidDataException();continue;
                }
                response.EnsureSuccessStatusCode();
                if(response.Content.Headers.ContentLength>MaximumBytes)throw new InvalidDataException();
                await using var source=await response.Content.ReadAsStreamAsync(timeout.Token);
                using var buffer=new MemoryStream();var chunk=new byte[16384];
                for(;;){var n=await source.ReadAsync(chunk,timeout.Token);if(n==0)break;if(buffer.Length+n>MaximumBytes)throw new InvalidDataException();buffer.Write(chunk,0,n);}
                var bytes=buffer.ToArray();ValidateContainer(bytes);
                lock(_cache){
                    if(!_disposed){
                        while(_cacheBytes+bytes.Length>24*1024*1024&&_cache.Count>0){var first=_cache.First();_cache.Remove(first.Key);_cacheBytes-=first.Value.Length;}
                        if(!_cache.ContainsKey(uri.AbsoluteUri)){_cache[uri.AbsoluteUri]=bytes;_cacheBytes+=bytes.Length;}
                    }
                }
                return bytes;
            }
            throw new InvalidDataException("Too many redirects.");
        }finally{_slots.Release();}
    }
    public static bool IsGif(byte[] bytes)=>bytes.Length>=6&&(bytes.AsSpan(0,6).SequenceEqual("GIF87a"u8)||bytes.AsSpan(0,6).SequenceEqual("GIF89a"u8));
    public static void CheckDimensions(int width,int height)
    {if(width<1||height<1||width>4096||height>4096||(long)width*height>4_000_000)throw new InvalidDataException("Media dimensions exceed the limit.");}
    public static void ValidateContainer(byte[] bytes)
    {
        if(bytes.Length<10||bytes.Length>MaximumBytes)throw new InvalidDataException();
        if(IsGif(bytes)){
            if(bytes.Length<13)throw new InvalidDataException();
            CheckDimensions(BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(6,2)),BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(8,2)));
            int p=13,frames=0;long pixels=0;
            if((bytes[10]&128)!=0)p+=3*(1<<((bytes[10]&7)+1));
            void Blocks(){while(true){if(p>=bytes.Length)throw new InvalidDataException();int n=bytes[p++];if(n==0)return;p+=n;if(p>bytes.Length)throw new InvalidDataException();}}
            while(p<bytes.Length){
                int marker=bytes[p++];if(marker==0x3b){if(frames==0)throw new InvalidDataException();return;}
                if(marker==0x21){p++;Blocks();continue;}
                if(marker!=0x2c||p+9>bytes.Length)throw new InvalidDataException();
                int w=BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(p+4,2)),h=BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(p+6,2));
                CheckDimensions(w,h);pixels+=(long)w*h;if(++frames>300||pixels>160_000_000)throw new InvalidDataException("GIF exceeds animation limit.");
                int packed=bytes[p+8];p+=9;if((packed&128)!=0)p+=3*(1<<((packed&7)+1));p++;Blocks();
            }
            throw new InvalidDataException();
        }
        if(bytes.AsSpan(0,8).SequenceEqual(new byte[]{137,80,78,71,13,10,26,10})){
            if(bytes.Length<24)throw new InvalidDataException();
            CheckDimensions(BinaryPrimitives.ReadInt32BigEndian(bytes.AsSpan(16,4)),BinaryPrimitives.ReadInt32BigEndian(bytes.AsSpan(20,4)));return;
        }
        if(bytes[0]==255&&bytes[1]==216)return; // JPEG dimensions are checked by the deferred WPF decoder before rasterization.
        throw new InvalidDataException("Only PNG, JPEG and GIF media is supported.");
    }
    public void Dispose(){_disposed=true;_http.Dispose();lock(_cache){_cache.Clear();_cacheBytes=0;}}
}
