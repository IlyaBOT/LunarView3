using System;
using System.IO;
using System.IO.Ports;
using System.Text;
using EpromDumper.Core;
namespace EpromDumper;
internal sealed class SerialLink : IDeviceLink, IDisposable {
    private readonly SerialPort port;
    private bool sessionStarted;
    public SerialLink(string name) {
        port=new SerialPort(name,115200,Parity.None,8,StopBits.One) {
            Handshake=Handshake.None, Encoding=Encoding.ASCII, NewLine="\n",
            ReadTimeout=200, WriteTimeout=1000, ReadBufferSize=65536, DtrEnable=false, RtsEnable=false
        };
    }
    public void Open() {
        port.Open(); port.DtrEnable=false; System.Threading.Thread.Sleep(30);
        port.DtrEnable=true; System.Threading.Thread.Sleep(350);
        port.DiscardInBuffer();
    }
    public int Read(byte[] buffer) => port.Read(buffer,0,buffer.Length);
    public void Write(string text) {
        port.Write(text);
        if(text=="CON:START\n") sessionStarted=true;
        if(text=="CON:STOP\n") sessionStarted=false;
    }
    public void Dispose() {
        try {
            if(port.IsOpen) {
                // Graceful idle disconnect uses Stop() and checks its reply first.
                // Cancellation/USB failure uses this best-effort close path.
                if(sessionStarted) { port.Write("CON:STOP\n"); sessionStarted=false; }
                port.DtrEnable=false;
            }
        }
        catch(Exception ex) when(ex is IOException || ex is InvalidOperationException || ex is UnauthorizedAccessException || ex is TimeoutException) { }
        try { port.Dispose(); }
        catch(Exception ex) when(ex is IOException || ex is InvalidOperationException || ex is UnauthorizedAccessException || ex is TimeoutException) { }
    }
}
