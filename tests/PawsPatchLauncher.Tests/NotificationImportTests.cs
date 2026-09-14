using PawsPatchLauncher;
using NAudio.Wave;
using Concentus;
using Concentus.Enums;
using Concentus.Oggfile;

internal static class NotificationImportTests
{
    internal static int Run(string root)
    {
        var checks=0;
        void Check(bool condition,string why){checks++;if(!condition)throw new Exception("Sound import: "+why);}
        Directory.CreateDirectory(root);
        var source=NotificationAudio.DefaultBytes(); var path=Path.Combine(root,"sound.mp3");
        File.WriteAllBytes(path,source);
        Check(NotificationSoundImporter.Import(path).SequenceEqual(source),"renamed PCM WAV changed");
        void Reject(SoundImportError reason)
        {
            try{NotificationSoundImporter.Import(path);throw new Exception("Accepted invalid sound");}
            catch(SoundImportException e){Check(e.Reason==reason,$"expected {reason}, got {e.Reason}");}
        }
        File.WriteAllBytes(path,new byte[NotificationSoundImporter.MaximumInputBytes+1]);Reject(SoundImportError.TooLarge);
        File.WriteAllBytes(path,new byte[12]);Reject(SoundImportError.Unsupported);
        File.WriteAllBytes(path,source[..20]);Reject(SoundImportError.Invalid);
        foreach(var seconds in new[]{1,15,16})
        {
            using(var writer=new WaveFileWriter(path,WaveFormat.CreateIeeeFloatWaveFormat(48000,2)))
            {
                var samples=Enumerable.Range(0,48000*2*seconds).Select(i=>(float)(.25*Math.Sin(i*.05))).ToArray();
                writer.WriteSamples(samples,0,samples.Length);
            }
            if(seconds>15){Reject(SoundImportError.TooLong);continue;}
            var result=NotificationSoundImporter.Import(path);NotificationAudio.Validate(result);
            using var reader=new WaveFileReader(new MemoryStream(result));
            Check(reader.WaveFormat.BitsPerSample==16 && reader.TotalTime.TotalSeconds>seconds-.03,"float WAV duration/PCM");
            Check(result.Length<=NotificationAudio.MaximumBytes,"converted WAV exceeds player limit");
        }
        foreach(var channels in new[]{1,2})
        {
            using(var output=File.Create(path))
            {
                var encoder=OpusCodecFactory.CreateEncoder(48000,channels,OpusApplication.OPUS_APPLICATION_AUDIO);
                var ogg=new OpusOggWriteStream(encoder,output,new OpusTags(),inputSampleRate:48000);
                var samples=Enumerable.Range(0,48000*channels).Select(i=>(short)(8000*Math.Sin(i*.05))).ToArray();
                ogg.WriteSamples(samples,0,samples.Length);ogg.Finish();
            }
            var result=NotificationSoundImporter.Import(path);NotificationAudio.Validate(result);
            using var reader=new WaveFileReader(new MemoryStream(result));
            Check(reader.TotalTime.TotalSeconds is >.95 and <1.1,"renamed Opus duration");
        }
        using var canceled=new CancellationTokenSource();canceled.Cancel();
        try{NotificationSoundImporter.Import(path,canceled.Token);throw new Exception("Canceled import continued");}
        catch(OperationCanceledException){checks++;}
        Console.WriteLine($"SOUND IMPORT PASS: {checks}"); return checks;
    }
    internal static void Files(string directory)
    {
        foreach(var path in Directory.GetFiles(directory).Where(p=>!p.EndsWith(".normalized.wav")))
        {
            var output=NotificationSoundImporter.Import(path);NotificationAudio.Validate(output);
            using var reader=new WaveFileReader(new MemoryStream(output));
            File.WriteAllBytes(path+".normalized.wav",output);
            Console.WriteLine($"{Path.GetFileName(path)}: PCM WAV {reader.TotalTime.TotalSeconds:F3}s / {output.Length} bytes");
        }
    }
}
