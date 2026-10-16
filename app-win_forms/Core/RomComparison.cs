using System;
using System.Collections;
using System.IO;
namespace EpromDumper.Core;

public sealed class RomComparison {
    private readonly BitArray differences;
    public int FileLength { get; }
    public int RomLength { get; }
    public int Length => differences.Length;
    public int Count { get; private set; }
    public int FirstAddress { get; private set; }=-1;
    public int LastAddress { get; private set; }=-1;
    public bool Identical => Count==0;
    public RomComparison(ReadOnlySpan<byte> file,ReadOnlySpan<byte> rom) {
        FileLength=file.Length; RomLength=rom.Length;
        differences=new BitArray(Math.Max(file.Length,rom.Length));
        for(int address=0;address<differences.Length;address++) {
            if(address<file.Length && address<rom.Length && file[address]==rom[address]) continue;
            differences[address]=true;
            if(Count++==0) FirstAddress=address;
            LastAddress=address;
        }
    }
    public bool IsDifferent(int address) => address>=0 && address<Length && differences[address];
}

public readonly record struct RomDifference(int Address,byte? FileByte,byte? RomByte) {
    public int BitMask => FileByte.HasValue && RomByte.HasValue ? FileByte.Value^RomByte.Value : 255;
    public string FileHex => FileByte?.ToString("X2") ?? "—";
    public string RomHex => RomByte?.ToString("X2") ?? "—";
    public string FileBinary => Binary(FileByte);
    public string RomBinary => Binary(RomByte);
    private static string Binary(byte? value) => value.HasValue ? Convert.ToString(value.Value,2).PadLeft(8,'0') : "--------";
}

public static class RomFile {
    public const int MaximumBytes=16*1024*1024;
    public static byte[] Load(string path) {
        string extension=Path.GetExtension(path).ToLowerInvariant();
        if(extension!=".bin" && extension!=".img" && extension!=".rom" && extension!=".dump")
            throw new InvalidDataException("Выберите ROM-файл с расширением .bin, .img, .rom или .dump.");
        using var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);
        if(stream.Length==0) throw new InvalidDataException("ROM-файл пуст.");
        if(stream.Length>MaximumBytes) throw new InvalidDataException("Максимальный размер открываемого ROM-файла — 16 МиБ.");
        var bytes=new byte[(int)stream.Length]; stream.ReadExactly(bytes);
        return bytes;
    }
}
