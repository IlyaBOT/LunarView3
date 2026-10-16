using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using EpromDumper.Core;
internal static class Program {
    static int passed;
    static void Check(bool condition,string name) { if(!condition) throw new Exception(name); passed++; Console.WriteLine("PASS "+name); }
    static void Reject(Action action,string name) { try { action(); } catch(InvalidDataException) { Check(true,name); return; } throw new Exception("Expected rejection: "+name); }
    static byte[] Reply(byte[] bytes) => Encoding.ASCII.GetBytes("ACK:"+Convert.ToHexString(bytes)+"\nCRC:"+Crc16.Compute(bytes).ToString("X4")+"\n");
    sealed class Link : IDeviceLink {
        readonly byte[] reply; int offset; readonly int step; public readonly List<string> Writes=new();
        public Link(byte[] reply,int step=1) { this.reply=reply; this.step=step; }
        public void Write(string text) { Writes.Add(text); }
        public int Read(byte[] buffer) { int n=Math.Min(step,Math.Min(buffer.Length,reply.Length-offset)); Array.Copy(reply,offset,buffer,0,n); offset+=n; return n; }
    }
    static void Main() {
        Check(DumperDisplay.Size(65536)=="65 536 байт (64КиБ/512КБит)","64 KiB size display");
        Check(DumperDisplay.Size(32768)=="32 768 байт (32КиБ/256КБит)" && DumperDisplay.Size(2048)=="2 048 байт (2КиБ/16КБит)","smaller ROM size display");
        Check(DumperDisplay.Size(512)=="512 байт (0,5КиБ/4КБит)","fractional KiB size display");
        Check(Crc16.Compute(Encoding.ASCII.GetBytes("123456789"))==0x29b1,"CRC known vector");
        byte[] small={0,1,0xa1,0xe2,0xbf,0x7,0x15,0xff}; byte[] wire=Reply(small);
        for(int split=0;split<=wire.Length;split++) {
            var p=new DumpParser(small.Length); p.Feed(wire,0,split); p.Feed(wire,split,wire.Length-split);
            if(!p.Complete || !p.Buffer.SequenceEqual(small)) throw new Exception("Boundary "+split);
        }
        Check(true,"all boundaries in ACK/HEX/CRC");
        foreach(int size in new[] {1,2048,32768,65536}) {
            byte[] source=Enumerable.Range(0,size).Select(i=>(byte)((i*73+(i>>8))&255)).ToArray();
            var p=new DumpParser(size); var link=new Link(Reply(source),size==65536?127:1);
            byte[] result=DumperSession.Read(link,p,null,CancellationToken.None);
            Check(result.SequenceEqual(source) && link.Writes.Single()==$"READ:{size}\n","stream "+size);
        }
        byte[] corrupt=(byte[])wire.Clone(); corrupt[4]=(byte)'F';
        Reject(()=>new DumpParser(small.Length).Feed(corrupt,0,corrupt.Length),"CRC detects valid-HEX corruption");
        foreach(string bad in new[] {"ACK:00G0\nCRC:FFFF\n", "ACK:0\n", "ACK:000102\n", "DATA:00\n", "ERR:SIZE\n", "ACK:0001\nCRC:XXXX\n"})
            Reject(()=> { var b=Encoding.ASCII.GetBytes(bad); new DumpParser(2).Feed(b,0,b.Length); },"malformed "+bad.Trim().Replace('\n','/'));
        var incomplete=new DumpParser(2); byte[] truncated=Encoding.ASCII.GetBytes("ACK:0001\nCRC:"); incomplete.Feed(truncated,0,truncated.Length);
        Check(!incomplete.Complete,"no completion before CRC terminator");
        var complete=new DumpParser(small.Length); complete.Feed(wire,0,wire.Length);
        Reject(()=>complete.Feed((byte)'F'),"trailing bytes rejected");
        string device="Lunar Dumper (Rev. 7) | Firmware: v.2.3.4 (build a8191hbz1) 12.10.2026";
        foreach(int chunk in new[] {1,3,256}) {
            var info=new Link(Encoding.ASCII.GetBytes("CON:"+device+"\r\n"+DumperSession.Identity+"\r\n"),chunk);
            Check(DumperSession.Handshake(info,CancellationToken.None)==device && info.Writes.Single()=="CON:START\n","identity handshake, chunk "+chunk);
        }
        Reject(()=>DumperSession.Handshake(new Link(Encoding.ASCII.GetBytes("INFO protocol=1\n")),CancellationToken.None),"Stage 2 firmware rejected");
        Reject(()=>DumperSession.Handshake(new Link(Encoding.ASCII.GetBytes("CON:device\nINFO:LITE1,MAX=65536,CRC16=1\n")),CancellationToken.None),"old Lite without PINS rejected");
        Reject(()=>DumperSession.Handshake(new Link(Encoding.ASCII.GetBytes(DumperSession.Identity+"\n")),CancellationToken.None),"capabilities without device identity rejected");
        var stopped=new Link(Encoding.ASCII.GetBytes("CON:STOP\n"),2); DumperSession.Stop(stopped,CancellationToken.None);
        Check(stopped.Writes.Single()=="CON:STOP\n","graceful disconnect sends STOP and checks ACK");
        Reject(()=>DumperSession.Stop(new Link(Encoding.ASCII.GetBytes("CON:UNKNOWN\n")),CancellationToken.None),"invalid STOP reply");
        foreach(string pins in new[] {"27C512","27C256","27C128"}) {
            var selected=new Link(Encoding.ASCII.GetBytes("ACK:PINS\n"),1); DumperSession.SelectPins(selected,pins,CancellationToken.None);
            Check(selected.Writes.Single()=="PINS:"+pins+"\n","select socket "+pins);
        }
        var unsupported=new Link(Array.Empty<byte>());
        Reject(()=>DumperSession.SelectPins(unsupported,"27C010",CancellationToken.None),"unsupported socket rejected before transmission");
        Check(unsupported.Writes.Count==0,"unsafe socket command not sent");
        using var cts=new CancellationTokenSource(); cts.Cancel();
        try { DumperSession.Read(new Link(wire),new DumpParser(small.Length),null,cts.Token); throw new Exception("cancel"); }
        catch(OperationCanceledException) { Check(true,"cancellation before transmission"); }
        try { DumperSession.Read(new Link(Encoding.ASCII.GetBytes("ACK:0")),new DumpParser(2),null,CancellationToken.None); throw new Exception("EOF"); }
        catch(IOException) { Check(true,"disconnect/truncated transfer"); }
        string fragments="<A id=\"\" size=\"65536\" page=\"1\" bus=\"parallel8\"/><B id=\"A13110\" size=\"65536\" page=\"256\" vcc=\"3.3\"/><C size=\"1\" page=\"SSTW\"/><D size=\"1\" page=\"SSTB\" pageep=\"4\" sizeeep=\"1024\"/>";
        var catalog=ChipCatalog.Parse(fragments);
        Check(catalog.Count==4 && catalog[0].Vcc==5 && catalog[0].Supported && !catalog[1].Supported,"adjacent XML fragments, VCC default, safe capability");
        Check(catalog[1].Id=="A13110" && catalog[2].Page=="SSTW" && catalog[3].Page=="SSTB" && catalog[3].PageEep==4 && catalog[3].SizeEep==1024,"all requested chip attributes");
        Reject(()=>ChipCatalog.Parse("<A size=\"1\"/><a size=\"2\"/>"),"duplicate chip names");
        Reject(()=>ChipCatalog.Parse("<A size=\"65536x\"/>"),"invalid decimal size");
        Reject(()=>ChipCatalog.Parse("<A size=\"1\" id=\"ZZ\"/>"),"invalid HEX ID");
        Reject(()=>ChipCatalog.Parse("<A size=\"1\" vcc=\"12\"/>"),"invalid VCC");
        Reject(()=>ChipCatalog.Parse("<A size=\"1\" page=\"byte\"/>"),"invalid page");
        var production=ChipCatalog.Load(Path.GetFullPath("app-win_forms/rom-chips.list"));
        Check(production.Count==4 && production.All(c=>c.Supported) && production.All(c=>!c.Name.StartsWith("ACE")),"production catalog without example chip");
        Check(production.Single(c=>c.Name=="NM27C256").Size==32768 && production.Single(c=>c.Name=="NM27C256").Pins=="27C256" &&
              production.Single(c=>c.Name=="NM27C128").Size==16384 && production.Single(c=>c.Name=="NM27C128").Pins=="27C128","capacity variants use appropriate socket controls");
        Check(!ChipCatalog.Parse("<A size=\"65536\" bus=\"parallel8\" pins=\"27C256\"/>")[0].Supported,"capacity exceeding pin profile blocked");
        Check(!ChipCatalog.Parse("<A size=\"2048\" bus=\"parallel8\" pins=\"random\"/>")[0].Supported,"unknown socket profile blocked");
        byte[] image={0x00,0xa0,0xff,0x15,0x01};
        var equal=new RomComparison(image,(byte[])image.Clone());
        Check(equal.Identical && equal.Count==0 && equal.FirstAddress==-1 && equal.LastAddress==-1,"identical ROM comparison");
        var changes=new RomComparison(image,new byte[] {0xff,0xa0,0xff,0x95,0x00});
        Check(changes.Count==3 && changes.FirstAddress==0 && changes.LastAddress==4 && changes.IsDifferent(0) && !changes.IsDifferent(1) && changes.IsDifferent(3) && changes.IsDifferent(4),"all mismatches counted, first and last including boundaries");
        var shortRom=new RomComparison(image,new byte[] {0x00,0xa0});
        Check(shortRom.Count==3 && shortRom.FirstAddress==2 && shortRom.LastAddress==4 && shortRom.Length==5,"longer file is not mistaken for matching ROM prefix");
        var longRom=new RomComparison(new byte[] {0x00},image);
        Check(longRom.Count==4 && longRom.FirstAddress==1 && longRom.LastAddress==4,"longer ROM missing file bytes counted");
        Check(!changes.IsDifferent(-1) && !changes.IsDifferent(5),"comparison padding is not marked as data");
        var bitDifference=new RomDifference(0x000c137e,0xa1,0x25);
        Check(bitDifference.BitMask==0x84 && bitDifference.FileBinary=="10100001" && bitDifference.RomBinary=="00100101" && bitDifference.FileHex=="A1" && bitDifference.RomHex=="25","tooltip XOR mask, MSB-first binary and HEX");
        var absent=new RomDifference(4,0xff,null);
        Check(absent.BitMask==255 && absent.RomHex=="—" && absent.RomBinary=="--------","missing bytes have explicit tooltip representation");
        foreach(int size in new[] {2048,32768,65536}) {
            var expected=Enumerable.Range(0,size).Select(i=>(byte)(i*31)).ToArray();
            var received=(byte[])expected.Clone(); received[size-1]^=0x80;
            var parsed=DumperSession.Read(new Link(Reply(received),127),new DumpParser(size),null,CancellationToken.None);
            var result=new RomComparison(expected,parsed);
            Check(result.Count==1 && result.FirstAddress==size-1 && result.LastAddress==size-1,"verified serial stream compared at last ROM address "+size);
        }
        string temp=Path.Combine(Path.GetTempPath(),"lunarview-rom-test-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(temp);
        try {
            foreach(string extension in new[] {".bin",".img",".rom",".dump",".BIN"}) {
                string path=Path.Combine(temp,"image"+extension); File.WriteAllBytes(path,image);
                Check(RomFile.Load(path).SequenceEqual(image),"raw file opens without altering bytes "+extension);
            }
            string empty=Path.Combine(temp,"empty.bin"); File.WriteAllBytes(empty,Array.Empty<byte>());
            Reject(()=>RomFile.Load(empty),"empty ROM image rejected");
            Reject(()=>RomFile.Load(Path.Combine(temp,"file.txt")),"unrequested ROM extension rejected");
            string large=Path.Combine(temp,"oversized.dump");
            using(var stream=File.Create(large)) stream.SetLength(RomFile.MaximumBytes+1);
            Reject(()=>RomFile.Load(large),"oversized image rejected before allocation");
        } finally { Directory.Delete(temp,true); }
        Console.WriteLine($"{passed} checks passed; no physical serial device used.");
    }
}
