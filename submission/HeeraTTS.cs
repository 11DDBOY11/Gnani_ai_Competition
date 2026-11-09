using System;
using System.IO;
using System.Threading.Tasks;
using Windows.Media.SpeechSynthesis;
using Windows.Storage.Streams;

class Program {
    static void Main(string[] args) {
        if (args.Length < 3) {
            Console.WriteLine("Usage: HeeraTTS <voicePattern> <outWav> <text>");
            return;
        }
        string voicePattern = args[0];
        string outPath = args[1];
        string text = args[2];
        Synthesize(voicePattern, outPath, text).GetAwaiter().GetResult();
    }

    static async Task Synthesize(string voicePattern, string outPath, string text) {
        using (var synth = new SpeechSynthesizer()) {
            foreach (var v in SpeechSynthesizer.AllVoices) {
                if (v.DisplayName.IndexOf(voicePattern, StringComparison.OrdinalIgnoreCase) >= 0 ||
                    v.Id.IndexOf(voicePattern, StringComparison.OrdinalIgnoreCase) >= 0) {
                    synth.Voice = v;
                    break;
                }
            }
            using (var stream = await synth.SynthesizeTextToStreamAsync(text)) {
                using (var reader = new DataReader(stream)) {
                    var bytes = new byte[stream.Size];
                    await reader.LoadAsync((uint)stream.Size);
                    reader.ReadBytes(bytes);
                    File.WriteAllBytes(outPath, bytes);
                }
            }
        }
        Console.WriteLine("Saved: " + outPath);
    }
}

