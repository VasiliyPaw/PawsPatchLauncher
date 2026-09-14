using System.Diagnostics;
using NAudio.Wave;
using NAudio.Wave.SampleProviders;
using NVorbis;
using Concentus;
using Concentus.Oggfile;

namespace PawsPatchLauncher;

public enum SoundImportError { TooLarge, TooLong, Unsupported, Invalid }
public sealed class SoundImportException(SoundImportError reason) : Exception(reason.ToString())
{
    public SoundImportError Reason { get; } = reason;
}

public static class NotificationSoundImporter
{
    public const int MaximumInputBytes = 20 * 1024 * 1024;
    public const int MaximumSeconds = 15;
    public const string Extensions = "*.wav;*.mp3;*.ogg;*.oga;*.opus;*.flac;*.m4a;*.aac;*.wma;*.aif;*.aiff";

    public static byte[] Import(string path, CancellationToken ct = default)
    {
        using var source = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (source.Length > MaximumInputBytes) throw new SoundImportException(SoundImportError.TooLarge);
        if (source.Length < 12) throw new SoundImportException(SoundImportError.Invalid);
        var bytes = new byte[checked((int)source.Length)]; source.ReadExactly(bytes);
        ct.ThrowIfCancellationRequested();
        var kind = Detect(bytes);
        if (kind == ".wav")
        {
            try { NotificationAudio.Validate(bytes); return bytes; }
            catch (InvalidDataException) { /* Float, extensible and compressed WAV need decoding too. */ }
        }
        try
        {
            if (kind == ".ogg")
            {
                using var reader = new VorbisSamples(new MemoryStream(bytes, false));
                return Normalize(reader, ct);
            }
            if (kind == ".opus")
            {
                using var stream = new MemoryStream(bytes, false);
                return Normalize(new OpusSamples(stream), ct);
            }
            if (kind == ".aiff")
            {
                using var reader = new AiffFileReader(new MemoryStream(bytes,false));
                return Normalize(reader.ToSampleProvider(),ct);
            }
            // A private copy with the detected extension also handles incorrectly named MP3/M4A/WAV.
            var temporary = Path.Combine(Path.GetTempPath(), "PawsSound-" + Guid.NewGuid().ToString("N") + kind);
            try
            {
                File.WriteAllBytes(temporary, bytes);
                using var reader = new MediaFoundationReader(temporary);
                return Normalize(reader.ToSampleProvider(), ct);
            }
            finally { File.Delete(temporary); }
        }
        catch (SoundImportException) { throw; }
        catch (OperationCanceledException) { throw; }
        catch (Exception e) when (e is not OutOfMemoryException and not StackOverflowException)
        { throw new SoundImportException(SoundImportError.Invalid); }
    }

    internal static string Detect(ReadOnlySpan<byte> bytes)
    {
        if (bytes.Length < 12) throw new SoundImportException(SoundImportError.Invalid);
        if (bytes.StartsWith("RIFF"u8) && bytes.Slice(8,4).SequenceEqual("WAVE"u8)) return ".wav";
        if (bytes.StartsWith("OggS"u8))
        {
            var header = bytes[..Math.Min(bytes.Length, 128)];
            if (header.IndexOf("OpusHead"u8) >= 0) return ".opus";
            if (header.IndexOf("\x01vorbis"u8) >= 0) return ".ogg";
            throw new SoundImportException(SoundImportError.Unsupported);
        }
        if (bytes.StartsWith("fLaC"u8)) return ".flac";
        if (bytes.Slice(4,4).SequenceEqual("ftyp"u8)) return ".m4a";
        if (bytes.StartsWith("ID3"u8) || bytes[0] == 0xff && (bytes[1] & 0xe6) == 0xe2) return ".mp3";
        if (bytes[0] == 0xff && (bytes[1] & 0xf6) == 0xf0) return ".aac";
        if (bytes.StartsWith(new byte[] {0x30,0x26,0xb2,0x75,0x8e,0x66,0xcf,0x11})) return ".wma";
        if (bytes.StartsWith("FORM"u8) && (bytes.Slice(8,4).SequenceEqual("AIFF"u8) || bytes.Slice(8,4).SequenceEqual("AIFC"u8))) return ".aiff";
        throw new SoundImportException(SoundImportError.Unsupported);
    }

    internal static byte[] Normalize(ISampleProvider source, CancellationToken ct)
    {
        var format = source.WaveFormat;
        if (format.Channels is not (1 or 2) || format.SampleRate is < 8000 or > 192000)
            throw new SoundImportException(SoundImportError.Unsupported);
        // 15 seconds of stereo PCM at 32 kHz fits the existing 2 MB playback limit.
        var bounded = new BoundedSamples(source, ct);
        ISampleProvider samples = format.SampleRate == 32000 ? bounded : new WdlResamplingSampleProvider(bounded, 32000);
        var pcm = new SampleToWaveProvider16(samples);
        using var output = new MemoryStream();
        using (var writer = new WaveFileWriter(new NAudio.Utils.IgnoreDisposeStream(output), pcm.WaveFormat))
        {
            var buffer = new byte[8192]; int read;
            while ((read = pcm.Read(buffer,0,buffer.Length)) > 0)
            {
                ct.ThrowIfCancellationRequested();
                if (output.Length + read > NotificationAudio.MaximumBytes) throw new SoundImportException(SoundImportError.TooLong);
                writer.Write(buffer,0,read);
            }
        }
        var result = output.ToArray(); NotificationAudio.Validate(result); return result;
    }

    private sealed class BoundedSamples(ISampleProvider source, CancellationToken ct) : ISampleProvider
    {
        private long _read;
        private readonly Stopwatch _time = Stopwatch.StartNew();
        public WaveFormat WaveFormat => source.WaveFormat;
        public int Read(float[] buffer,int offset,int count)
        {
            ct.ThrowIfCancellationRequested();
            if (_time.Elapsed > TimeSpan.FromSeconds(15)) throw new SoundImportException(SoundImportError.Invalid);
            var read=source.Read(buffer,offset,count); _read+=read;
            if (_read > (long)WaveFormat.SampleRate * WaveFormat.Channels * MaximumSeconds)
                throw new SoundImportException(SoundImportError.TooLong);
            for (var i=offset;i<offset+read;i++) if(!float.IsFinite(buffer[i])) throw new SoundImportException(SoundImportError.Invalid);
            return read;
        }
    }
    private sealed class VorbisSamples : ISampleProvider, IDisposable
    {
        private readonly VorbisReader _reader;
        public VorbisSamples(Stream stream) { _reader = new VorbisReader(stream,true); }
        public WaveFormat WaveFormat => WaveFormat.CreateIeeeFloatWaveFormat(_reader.SampleRate,_reader.Channels);
        public int Read(float[] buffer,int offset,int count) => _reader.ReadSamples(buffer,offset,count);
        public void Dispose() => _reader.Dispose();
    }
    private sealed class OpusSamples : ISampleProvider
    {
        private readonly OpusOggReadStream _reader;
        private short[] _packet=[];
        private int _offset;
        private int _skip;
        private long _remaining;
        private readonly float _gain;
        public OpusSamples(Stream stream)
        {
            var header=new byte[128];var count=stream.Read(header);stream.Position=0;
            var start=header.AsSpan(0,count).IndexOf("OpusHead"u8);
            if(start<0 || start+19>count || header[start+18]!=0)throw new SoundImportException(SoundImportError.Unsupported);
            var preSkip=System.Buffers.Binary.BinaryPrimitives.ReadUInt16LittleEndian(header.AsSpan(start+10,2));
            var gain=System.Buffers.Binary.BinaryPrimitives.ReadInt16LittleEndian(header.AsSpan(start+16,2));
            _gain=(float)Math.Pow(10,gain/(20d*256));
            _reader=new OpusOggReadStream(OpusCodecFactory.CreateDecoder(48000,2),stream);
            _skip=preSkip*2;_remaining=(_reader.GranuleCount-preSkip)*2;
            if(_remaining<=0)throw new SoundImportException(SoundImportError.Invalid);
            if(_remaining>48000L*2*MaximumSeconds)throw new SoundImportException(SoundImportError.TooLong);
        }
        public WaveFormat WaveFormat { get; } = WaveFormat.CreateIeeeFloatWaveFormat(48000,2);
        public int Read(float[] buffer,int offset,int count)
        {
            var written=0;
            while(written<count && _remaining>0)
            {
                if(_offset==_packet.Length)
                {
                    if(!_reader.HasNextPacket)
                    {
                        throw new SoundImportException(SoundImportError.Invalid);
                    }
                    var next=_reader.DecodeNextPacket();
                    if(next is null)
                    {
                        throw new SoundImportException(SoundImportError.Invalid);
                    }
                    _packet=next;
                    _offset=0;
                    if(_packet.Length==0)throw new SoundImportException(SoundImportError.Invalid);
                }
                if(_skip>0){var skip=Math.Min(_skip,_packet.Length-_offset);_skip-=skip;_offset+=skip;continue;}
                var take=(int)Math.Min(_remaining,Math.Min(count-written,_packet.Length-_offset));
                for(var i=0;i<take;i++)buffer[offset+written+i]=_packet[_offset+i]/32768f*_gain;
                _offset+=take;written+=take;_remaining-=take;
            }
            return written;
        }
    }
}
