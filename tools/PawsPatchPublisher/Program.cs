using PawsPatchLauncher;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;

if (args.Length == 0)
{
    Usage();
    return 2;
}

try
{
    switch (args[0].ToLowerInvariant())
    {
        case "pack" when args.Length == 5:
            await PackAsync(args[1], args[2], args[3], args[4]);
            break;
        case "keygen" when args.Length == 2:
            Keygen(args[1]);
            break;
        case "sign" when args.Length == 5:
            Sign(args[1], args[2], args[3], args[4]);
            break;
        case "verify" when args.Length == 3:
            Verify(args[1], args[2]);
            break;
        default:
            Usage();
            return 2;
    }
    return 0;
}
catch (Exception ex)
{
    Console.Error.WriteLine(ex.ToString());
    return 1;
}

static async Task PackAsync(string id, string version, string sourceArgument, string outputArgument)
{
    var source = Path.GetFullPath(sourceArgument);
    var output = Path.GetFullPath(outputArgument);
    if (!Directory.Exists(source)) throw new DirectoryNotFoundException(source);
    Directory.CreateDirectory(Path.GetDirectoryName(output)!);

    var temporary = Path.Combine(Path.GetTempPath(), "PawsPatchPublisher", Guid.NewGuid().ToString("N"));
    var payload = Path.Combine(temporary, "payload");
    Directory.CreateDirectory(payload);
    try
    {
        var manifest = new ModuleArchiveManifest { Id = id, Version = version };
        var removalsPath = Path.Combine(source, ".pawpatch-remove.txt");
        if (File.Exists(removalsPath))
        {
            manifest.Remove = File.ReadAllLines(removalsPath)
                .Select(line => line.Trim())
                .Where(line => line.Length > 0 && !line.StartsWith('#'))
                .Select(CryptoAndIO.NormalizeRelativePath)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();
            foreach (var relative in manifest.Remove) CryptoAndIO.SafeChildPath(source, relative);
        }
        foreach (var file in Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
        {
            var relative = CryptoAndIO.NormalizeRelativePath(Path.GetRelativePath(source, file));
            if (relative.Equals("module.json", StringComparison.OrdinalIgnoreCase) || relative.Equals(".pawpatch-remove.txt", StringComparison.OrdinalIgnoreCase)) continue;
            if (manifest.Remove.Contains(relative, StringComparer.OrdinalIgnoreCase))
                throw new InvalidDataException($"Package both installs and removes: {relative}");
            var target = CryptoAndIO.SafeChildPath(payload, relative);
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            File.Copy(file, target, true);
            manifest.Files.Add(new ModuleFile
            {
                Path = relative,
                Size = new FileInfo(file).Length,
                Sha256 = await CryptoAndIO.Sha256Async(file)
            });
        }
        await File.WriteAllTextAsync(Path.Combine(temporary, "module.json"),
            JsonSerializer.Serialize(manifest, LauncherJsonContext.Default.ModuleArchiveManifest));
        if (File.Exists(output)) File.Delete(output);
        ZipFile.CreateFromDirectory(temporary, output, CompressionLevel.SmallestSize, false);
        Console.WriteLine($"PACKED {id} {version} {manifest.Files.Count} files {manifest.Remove.Count} removals {new FileInfo(output).Length} bytes {await CryptoAndIO.Sha256Async(output)}");
    }
    finally { try { Directory.Delete(temporary, true); } catch { } }
}

static void Keygen(string directoryArgument)
{
    var directory = Path.GetFullPath(directoryArgument);
    Directory.CreateDirectory(directory);
    var privatePath = Path.Combine(directory, "pawpatch-signing-private.pem");
    var publicPath = Path.Combine(directory, "pawpatch-signing-public.pem");
    if (File.Exists(privatePath) || File.Exists(publicPath))
        throw new IOException("Refusing to overwrite an existing signing key.");
    using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
    File.WriteAllText(privatePath, key.ExportECPrivateKeyPem());
    File.WriteAllText(publicPath, key.ExportSubjectPublicKeyInfoPem());
    Console.WriteLine($"CREATED {privatePath}");
    Console.WriteLine($"CREATED {publicPath}");
    Console.WriteLine("Keep the private key offline and never publish it.");
}

static void Sign(string manifestArgument, string privateKeyArgument, string keyId, string outputArgument)
{
    var payload = File.ReadAllBytes(Path.GetFullPath(manifestArgument));
    using var key = ECDsa.Create();
    key.ImportFromPem(File.ReadAllText(Path.GetFullPath(privateKeyArgument)));
    var signature = key.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
    var envelope = new SignedFeedEnvelope { KeyId = keyId, Payload = Convert.ToBase64String(payload), Signature = Convert.ToBase64String(signature) };
    var output = Path.GetFullPath(outputArgument);
    Directory.CreateDirectory(Path.GetDirectoryName(output)!);
    File.WriteAllText(output, JsonSerializer.Serialize(envelope, LauncherJsonContext.Default.SignedFeedEnvelope));
    Console.WriteLine($"SIGNED {output}");
}

static void Verify(string envelopeArgument, string publicKeyArgument)
{
    var envelope = JsonSerializer.Deserialize(File.ReadAllText(Path.GetFullPath(envelopeArgument)), LauncherJsonContext.Default.SignedFeedEnvelope)
                   ?? throw new InvalidDataException("Envelope is empty.");
    var payload = Convert.FromBase64String(envelope.Payload);
    var valid = CryptoAndIO.VerifySignature(payload, envelope.Signature, File.ReadAllText(Path.GetFullPath(publicKeyArgument)));
    if (!valid) throw new CryptographicException("Signature is invalid.");
    var manifest = JsonSerializer.Deserialize(payload, LauncherJsonContext.Default.ChannelManifest)
                   ?? throw new InvalidDataException("Manifest is empty.");
    Console.WriteLine($"VALID {manifest.Channel} {manifest.Packages.Count} packages");
}

static void Usage()
{
    Console.WriteLine("PawsPatchPublisher commands:");
    Console.WriteLine("  pack <id> <version> <source-directory> <output.zip>");
    Console.WriteLine("  keygen <private-output-directory>");
    Console.WriteLine("  sign <channel.json> <private.pem> <key-id> <signed-output.json>");
    Console.WriteLine("  verify <signed-feed.json> <public.pem>");
}
