using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
namespace EpromDumper.Core;
public interface IDeviceLink { int Read(byte[] buffer); void Write(string text); }
public static class DumperSession {
    public const string Identity="INFO:LITE2,MAX=65536,CRC16=1,PINS=1";
    private static void Lines(IDeviceLink link, string command, Func<string,bool> consume, CancellationToken token, int timeout=4000) {
        token.ThrowIfCancellationRequested(); link.Write(command+"\n");
        var deadline=Stopwatch.StartNew(); var line=new StringBuilder(); var buffer=new byte[256];
        while(deadline.ElapsedMilliseconds<timeout) {
            token.ThrowIfCancellationRequested();
            int n;
            try { n=link.Read(buffer); } catch(TimeoutException) { continue; }
            if(n==0) throw new IOException("COM-порт закрылся.");
            bool finished=false;
            for(int i=0;i<n;i++) {
                if(finished) throw new InvalidDataException("Лишние данные после ответа устройства.");
                if(buffer[i]=='\r') continue;
                if(buffer[i]=='\n') {
                    string answer=line.ToString(); line.Clear();
                    if(answer.StartsWith("ERR:",StringComparison.Ordinal)) throw new InvalidDataException("Устройство: "+answer);
                    finished=consume(answer);
                } else {
                    if(buffer[i]<32 || buffer[i]>126 || line.Length>=256) throw new InvalidDataException("Повреждён ответ устройства.");
                    line.Append((char)buffer[i]);
                }
            }
            if(finished) return;
        }
        throw new TimeoutException("Нет ответа на "+command+" при 115200 бод.");
    }
    public static string Handshake(IDeviceLink link,CancellationToken token) {
        string? identity=null;
        Lines(link,"CON:START",answer=> {
            if(identity==null && answer.StartsWith("CON:",StringComparison.Ordinal) && answer.Length>4) {
                identity=answer.Substring(4); return false;
            }
            if(identity!=null && answer==Identity) return true;
            throw new InvalidDataException("Подключена несовместимая прошивка: "+answer);
        },token);
        return identity!;
    }
    public static void Stop(IDeviceLink link,CancellationToken token) => Lines(link,"CON:STOP",answer=> {
        if(answer!="CON:STOP") throw new InvalidDataException("Некорректный ответ на CON:STOP: "+answer);
        return true;
    },token,2000);
    public static void SelectPins(IDeviceLink link,string pins,CancellationToken token) {
        if(pins!="27C512" && pins!="27C256" && pins!="27C128") throw new InvalidDataException("Неизвестный режим выводов ROM.");
        Lines(link,"PINS:"+pins,answer=> {
            if(answer!="ACK:PINS") throw new InvalidDataException("Некорректный ответ на PINS: "+answer);
            return true;
        },token);
    }
    public static byte[] Read(IDeviceLink link,DumpParser parser,Action<int>? progress,CancellationToken token) {
        token.ThrowIfCancellationRequested();
        link.Write($"READ:{parser.Buffer.Length}\n");
        var elapsed=Stopwatch.StartNew(); var idle=Stopwatch.StartNew(); long lastProgress=0;
        var bytes=new byte[1024];
        double totalSeconds=10+parser.Buffer.Length/2000.0;
        while(!parser.Complete) {
            token.ThrowIfCancellationRequested();
            if(idle.ElapsedMilliseconds>=3000 || elapsed.Elapsed.TotalSeconds>totalSeconds)
                throw new TimeoutException($"Чтение прервано: получено {parser.Count} из {parser.Buffer.Length} байт.");
            int n;
            try { n=link.Read(bytes); } catch(TimeoutException) { continue; }
            if(n==0) throw new IOException("COM-порт закрылся во время чтения.");
            idle.Restart(); parser.Feed(bytes,0,n);
            if(elapsed.ElapsedMilliseconds-lastProgress>=75 || parser.Complete) { progress?.Invoke(parser.Count); lastProgress=elapsed.ElapsedMilliseconds; }
        }
        return parser.Buffer;
    }
}
