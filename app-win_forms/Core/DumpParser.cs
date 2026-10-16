using System;
using System.IO;
using System.Text;
namespace EpromDumper.Core;
public static class Crc16 {
    public static ushort Add(ushort crc, byte b) {
        crc ^= (ushort)(b << 8);
        for (int i=0;i<8;i++) crc=(ushort)((crc&0x8000)!=0 ? (crc<<1)^0x1021 : crc<<1);
        return crc;
    }
    public static ushort Compute(byte[] bytes) { ushort crc=0xffff; foreach(byte b in bytes) crc=Add(crc,b); return crc; }
}
/* Consumes arbitrary serial chunks, including splits inside ACK:, a byte or CRC.
   Complete becomes true only after exact length, terminators and valid CRC. */
public sealed class DumpParser {
    private enum State { Header, Error, Hex, EndHex, CrcHeader, CrcHex, EndCrc, Done }
    private State state=State.Header;
    private readonly StringBuilder text=new();
    private int high=-1, crcDigits;
    private ushort crc=0xffff, reported;
    public byte[] Buffer { get; }
    public int Count { get; private set; }
    public bool Complete => state==State.Done;
    public ushort Checksum => crc;
    public DumpParser(int size) {
        if(size<1 || size>65536) throw new ArgumentOutOfRangeException(nameof(size));
        Buffer=new byte[size];
    }
    public void Feed(byte[] bytes,int offset,int count) {
        if(offset<0 || count<0 || offset>bytes.Length-count) throw new ArgumentOutOfRangeException();
        for(int i=offset;i<offset+count;i++) Feed(bytes[i]);
    }
    private static int Nibble(byte c) => c>='0'&&c<='9' ? c-'0' : c>='A'&&c<='F' ? c-'A'+10 : c>='a'&&c<='f' ? c-'a'+10 : -1;
    public void Feed(byte c) {
        if(c=='\r' && (state==State.EndHex || state==State.EndCrc || state==State.Error)) return;
        switch(state) {
        case State.Header:
            if(c==':') {
                string key=text.ToString(); text.Clear();
                if(key=="ACK") state=State.Hex;
                else if(key=="ERR") state=State.Error;
                else throw new InvalidDataException("Ожидался ACK:, получено "+key+":");
            } else {
                if(c<32 || c>126 || text.Length>=16) throw new InvalidDataException("Повреждён заголовок ответа.");
                text.Append((char)c);
            }
            break;
        case State.Error:
            if(c=='\n') throw new InvalidDataException("Устройство: "+text);
            if(c<32 || c>126 || text.Length>=128) throw new InvalidDataException("Повреждён ERR.");
            text.Append((char)c); break;
        case State.Hex:
            int n=Nibble(c);
            if(n<0) throw new InvalidDataException("Обрыв или не-HEX символ в данных ROM.");
            if(high<0) high=n;
            else {
                byte value=(byte)((high<<4)|n); high=-1;
                Buffer[Count++]=value; crc=Crc16.Add(crc,value);
                if(Count==Buffer.Length) state=State.EndHex;
            }
            break;
        case State.EndHex:
            if(c!='\n') throw new InvalidDataException("Лишние данные после ожидаемого объёма ROM.");
            state=State.CrcHeader; break;
        case State.CrcHeader:
            const string prefix="CRC:";
            if(c!=prefix[text.Length]) throw new InvalidDataException("Отсутствует строка CRC:.");
            text.Append((char)c);
            if(text.Length==4) { text.Clear(); state=State.CrcHex; }
            break;
        case State.CrcHex:
            int digit=Nibble(c);
            if(digit<0) throw new InvalidDataException("Повреждена контрольная сумма.");
            reported=(ushort)((reported<<4)|digit);
            if(++crcDigits==4) state=State.EndCrc;
            break;
        case State.EndCrc:
            if(c!='\n') throw new InvalidDataException("Лишние символы в CRC.");
            if(reported!=crc) throw new InvalidDataException($"Ошибка CRC: устройство {reported:X4}, компьютер {crc:X4}.");
            state=State.Done; break;
        default: throw new InvalidDataException("Неожиданные данные после завершения чтения.");
        }
    }
}
