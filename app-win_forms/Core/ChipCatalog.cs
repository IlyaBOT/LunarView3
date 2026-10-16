using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Xml;
using System.Xml.Linq;
namespace EpromDumper.Core;
public sealed class RomChip {
    public string Name { get; init; }="";
    public int Size { get; init; }
    public string Id { get; init; }="";
    public string Page { get; init; }="";
    public int? PageEep { get; init; }
    public int? SizeEep { get; init; }
    public decimal Vcc { get; init; }=5m;
    public string Adapter { get; init; }="";
    public string Pins { get; init; }="27C512";
    public string Comment { get; init; }="";
    /* Imported SPI/AVR metadata is retained, but does not grant hardware support. */
    public string Bus { get; init; }="unknown";
    public bool Supported => Bus=="parallel8" && Size<=PinCapacity && Vcc==5m;
    private int PinCapacity => Pins switch { "27C512"=>65536, "27C256"=>32768, "27C128"=>16384, _=>0 };
    public string BlockReason => Supported ? "" : "Для этой записи нужен другой интерфейс/питание; Lite читает parallel8, 5 В, до 65536 байт.";
    public override string ToString() => $"{Name} ({Size/1024.0:0.##} КиБ){(Supported ? "" : " — недоступно на Lite")}";
}
public static class ChipCatalog {
    public static IReadOnlyList<RomChip> Load(string path) => Parse(File.ReadAllText(path));
    public static IReadOnlyList<RomChip> Parse(string source) {
        // A list of standalone <CHIP .../> elements is the file format; no root required.
        var settings=new XmlReaderSettings { ConformanceLevel=ConformanceLevel.Fragment, DtdProcessing=DtdProcessing.Prohibit, XmlResolver=null };
        var chips=new List<RomChip>();
        var names=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        using var reader=XmlReader.Create(new StringReader(source),settings);
        while(reader.Read()) {
            if(reader.NodeType!=XmlNodeType.Element) continue;
            var e=(XElement)XNode.ReadFrom(reader);
            ParseElement(e,chips,names);
            // ReadFrom advances beyond the element; process the next current element too.
            while(reader.NodeType==XmlNodeType.Element) {
                e=(XElement)XNode.ReadFrom(reader); ParseElement(e,chips,names);
            }
        }
        if(chips.Count==0) throw new InvalidDataException("rom-chips.list не содержит микросхем.");
        return chips;
    }
    private static void ParseElement(XElement e,List<RomChip> result,HashSet<string> names) {
        if(e.HasElements || !string.IsNullOrWhiteSpace(e.Value)) throw new InvalidDataException("Каждая запись должна иметь вид <CHIP .../>.");
        string name=e.Name.LocalName;
        if(!names.Add(name)) throw new InvalidDataException("Повторная запись: "+name);
        string Get(string key,string fallback="") => e.Attribute(key)?.Value ?? fallback;
        int Number(string key,bool required) {
            string value=Get(key);
            if(!required && value.Length==0) return -1;
            if(!int.TryParse(value,NumberStyles.None,CultureInfo.InvariantCulture,out int n) || n<0 || (required && n==0))
                throw new InvalidDataException($"{name}: {key} должен быть десятичным числом.");
            return n;
        }
        int size=Number("size",true);
        string id=Get("id");
        if(id.Length!=0 && (id.Length%2!=0 || id.Any(c=>!Uri.IsHexDigit(c)))) throw new InvalidDataException(name+": id должен быть HEX с целым числом байтов.");
        string page=Get("page");
        if(page.Length>0 && page!="SSTW" && page!="SSTB" && (!int.TryParse(page,NumberStyles.None,CultureInfo.InvariantCulture,out int p)||p<1))
            throw new InvalidDataException(name+": page должен быть числом, SSTW или SSTB.");
        if(!decimal.TryParse(Get("vcc","5.0"),NumberStyles.AllowDecimalPoint,CultureInfo.InvariantCulture,out decimal vcc) || (vcc!=3.3m && vcc!=5m))
            throw new InvalidDataException(name+": vcc должен быть 3.3 или 5.0.");
        int pe=Number("pageep",false), se=Number("sizeeep",false);
        result.Add(new RomChip { Name=name, Size=size, Id=id.ToUpperInvariant(), Page=page, Pins=Get("pins","27C512"),
            PageEep=pe<0?null:pe, SizeEep=se<0?null:se, Vcc=vcc, Adapter=Get("adapt"), Comment=Get("comment"), Bus=Get("bus","unknown") });
    }
}
