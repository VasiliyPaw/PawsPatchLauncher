using System.Buffers.Binary;
using System.Media;

namespace PawsPatchLauncher;

public sealed class NotificationAudio : IDisposable
{
    public const int MaximumBytes = 2 * 1024 * 1024;
    public static bool HasNewArrival(IReadOnlyList<SocialPlayer> previous,IReadOnlyList<SocialPlayer> current)
        => current.Any(p=>p.Relation=="incoming"&&!previous.Any(old=>old.Id==p.Id&&old.Relation=="incoming")
            ||p.Relation=="friend"&&p.Unread>(previous.FirstOrDefault(old=>old.Id==p.Id)?.Unread??0));
    private SoundPlayer? _player;
    private MemoryStream? _stream;
    public static void Validate(byte[] wav)
    {
        if (wav.Length is < 44 or > MaximumBytes || !wav.AsSpan(0,4).SequenceEqual("RIFF"u8) || !wav.AsSpan(8,4).SequenceEqual("WAVE"u8))
            throw new InvalidDataException("Use a PCM WAV, up to 2 MB and 15 seconds.");
        var rate = 0; var data = 0; var format = false;
        for (var pos = 12; pos <= wav.Length-8;)
        {
            var len = BinaryPrimitives.ReadUInt32LittleEndian(wav.AsSpan(pos+4,4));
            if (len > wav.Length-pos-8) throw new InvalidDataException("Invalid WAV chunk.");
            if (wav.AsSpan(pos,4).SequenceEqual("fmt "u8))
            {
                if (len < 16 || BinaryPrimitives.ReadUInt16LittleEndian(wav.AsSpan(pos+8,2)) != 1) throw new InvalidDataException("Use a PCM WAV.");
                var channels = BinaryPrimitives.ReadUInt16LittleEndian(wav.AsSpan(pos+10,2));
                var hz = BinaryPrimitives.ReadInt32LittleEndian(wav.AsSpan(pos+12,4));
                rate = BinaryPrimitives.ReadInt32LittleEndian(wav.AsSpan(pos+16,4));
                var bits = BinaryPrimitives.ReadUInt16LittleEndian(wav.AsSpan(pos+22,2));
                if (channels is <1 or >2 || hz is <8000 or >192000 || bits is not (8 or 16 or 24 or 32) || rate != hz*channels*bits/8)
                    throw new InvalidDataException("Unsupported PCM WAV.");
                format = true;
            }
            if (wav.AsSpan(pos,4).SequenceEqual("data"u8)) data = checked(data+(int)len);
            pos = checked(pos+8+(int)len+((int)len&1));
        }
        if (!format || data == 0 || rate <= 0 || data > rate*15) throw new InvalidDataException("Use a sound up to 15 seconds.");
    }
    public static byte[] DefaultBytes()
    {
        using var source = typeof(NotificationAudio).Assembly.GetManifestResourceStream("PawsPatchLauncher.Assets.notification-soft-pluck.wav")!;
        using var output = new MemoryStream(); source.CopyTo(output); return output.ToArray();
    }
    public static byte[] WithVolume(byte[] bytes,double volume)
    {
        Validate(bytes);volume=double.IsFinite(volume)?Math.Clamp(volume,0,1):1;
        var result=(byte[])bytes.Clone();int bits=0;
        for(int p=12;p<=bytes.Length-8;){
            var n=(int)BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(p+4,4));
            if(bytes.AsSpan(p,4).SequenceEqual("fmt "u8))bits=BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(p+22,2));
            p+=8+n+(n&1);
        }
        for(int p=12;p<=bytes.Length-8;){
            var n=(int)BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(p+4,4));
            if(bytes.AsSpan(p,4).SequenceEqual("data"u8)){
                var step=bits/8;if(n%step!=0)throw new InvalidDataException("Incomplete PCM sample.");
                for(int i=p+8;i<p+8+n;i+=step){
                    long sample=bits switch {
                        8=>bytes[i]-128,
                        16=>BinaryPrimitives.ReadInt16LittleEndian(bytes.AsSpan(i,2)),
                        24=>(bytes[i]|bytes[i+1]<<8|bytes[i+2]<<16)<<8>>8,
                        _=>BinaryPrimitives.ReadInt32LittleEndian(bytes.AsSpan(i,4))};
                    var scaled=(int)Math.Round(sample*volume);
                    if(bits==8)result[i]=(byte)(scaled+128);
                    else for(int j=0;j<step;j++)result[i+j]=(byte)(scaled>>(8*j));
                }
            }
            p+=8+n+(n&1);
        }
        return result;
    }
    public void Play(byte[] bytes,double volume=1)
    {
        Validate(bytes); Dispose();
        _stream = new MemoryStream(WithVolume(bytes,volume), false); _player = new SoundPlayer(_stream); _player.Load(); _player.Play();
    }
    public void Dispose() { _player?.Stop(); _player?.Dispose(); _stream?.Dispose(); _player = null; _stream = null; }
}
