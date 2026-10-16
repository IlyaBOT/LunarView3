using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using EpromDumper;
using EpromDumper.Core;

static class Program {
    private static int passed;
    private static void Check(bool condition,string name) {
        if(!condition) throw new Exception(name); passed++; Console.WriteLine("PASS "+name);
    }
    private sealed class Link : IDeviceLink {
        private readonly Queue<byte> queue=new();
        private readonly byte[] rom;
        private readonly bool corruptCrc;
        private readonly bool failRead;
        public readonly List<string> Writes=new();
        public Link(byte[] rom,bool corruptCrc=false,bool failRead=false) { this.rom=rom; this.corruptCrc=corruptCrc; this.failRead=failRead; }
        public void Write(string text) {
            Writes.Add(text);
            if(failRead && text.StartsWith("READ:",StringComparison.Ordinal)) throw new IOException("Имитированный обрыв соединения при чтении ROM.");
            string response=text.StartsWith("PINS:",StringComparison.Ordinal) ? "ACK:PINS\n" :
                "ACK:"+Convert.ToHexString(rom)+"\nCRC:"+((ushort)(Crc16.Compute(rom)^(corruptCrc?1:0))).ToString("X4")+"\n";
            foreach(byte value in Encoding.ASCII.GetBytes(response)) queue.Enqueue(value);
        }
        public int Read(byte[] buffer) {
            int count=Math.Min(5,Math.Min(buffer.Length,queue.Count));
            for(int i=0;i<count;i++) buffer[i]=queue.Dequeue(); return count;
        }
    }
    [STAThread] static void Main(string[] args) {
        ApplicationConfiguration.Initialize();
        if(args.Length==2 && args[0]=="--window-preview") {
            using var view=new MainForm(new[] {"--demo"});
            using var timer=new System.Windows.Forms.Timer { Interval=300 };
            view.Shown+=(_,_)=>timer.Start();
            timer.Tick+=(_,_)=> {
                timer.Stop();
                try {
                    var root=(TableLayoutPanel)view.Controls[0];
                    var bar=root.Controls.OfType<FlowLayoutPanel>().Single();
                    var hex=(DataGridView)typeof(MainForm).GetField("grid",BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(view)!;
                    if(bar.HorizontalScroll.Visible || bar.Controls.Cast<Control>().Any(c=>c.Right>bar.ClientSize.Width))
                        throw new Exception("Toolbar does not fit the window");
                    if(hex.Controls.OfType<HScrollBar>().Any(scroll=>scroll.Visible))
                        throw new Exception("HEX and ASCII columns do not fit the window");
                    string path=Path.GetFullPath(args[1]); Directory.CreateDirectory(Path.GetDirectoryName(path)!);
                    using var image=new Bitmap(view.Width,view.Height);
                    view.DrawToBitmap(image,new Rectangle(0,0,view.Width,view.Height)); image.Save(path);
                    Console.WriteLine($"Rendered {view.Width}×{view.Height}; toolbar, 16 HEX columns and ASCII fit without horizontal scrolling.");
                } catch(Exception ex) { Console.Error.WriteLine(ex); Environment.ExitCode=1; }
                finally { view.Close(); }
            };
            Application.Run(view);
            return;
        }
        if(args.Length==2 && args[0]=="--tooltip-preview") {
            Directory.CreateDirectory(args[1]);
            foreach(float scale in new[] {1f,1.5f}) {
                var size=DifferenceToolTip.GetSize(scale);
                using var tooltip=new Bitmap(size.Width,size.Height);
                using var graphics=Graphics.FromImage(tooltip);
                DifferenceToolTip.Paint(graphics,size,new RomDifference(0x000c137e,0xa1,0x25),scale);
                tooltip.Save(Path.Combine(args[1],"difference-tooltip-"+(int)(scale*100)+".png"));
            }
            var missingSize=DifferenceToolTip.GetSize();
            using var missing=new Bitmap(missingSize.Width,missingSize.Height);
            using var missingGraphics=Graphics.FromImage(missing);
            DifferenceToolTip.Paint(missingGraphics,missingSize,new RomDifference(0x00000010,0xff,null));
            missing.Save(Path.Combine(args[1],"difference-tooltip-missing.png"));
            Console.WriteLine("Rendered tooltip previews at 100%/150% DPI and missing-byte case.");
            return;
        }
        var messages=new List<(string Text,string Title,MessageBoxIcon Icon)>();
        using var form=new MainForm(Array.Empty<string>(),(text,title,icon)=>messages.Add((text,title,icon)));
        object? Field(string name)=>typeof(MainForm).GetField(name,BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(form);
        object? Call(string name,params object[] values)=>typeof(MainForm).GetMethod(name,BindingFlags.Instance|BindingFlags.NonPublic)!.Invoke(form,values);
        var grid=(DataGridView)Field("grid")!;
        var styles=new Dictionary<int,(Color Back,Color Fore,Color SelectedBack,Color SelectedFore)>();
        grid.CellFormatting+=(_,e)=> {
            if(e.RowIndex>=0 && e.ColumnIndex>=1 && e.ColumnIndex<=16)
                styles[e.RowIndex*16+e.ColumnIndex-1]=(e.CellStyle!.BackColor,e.CellStyle.ForeColor,e.CellStyle.SelectionBackColor,e.CellStyle.SelectionForeColor);
        };
        void FormatCells(int count) {
            styles.Clear();
            for(int i=0;i<count;i++) _=grid.Rows[i/16].Cells[i%16+1].FormattedValue;
        }
        void Locks() {
            foreach(string name in new[] {"ports","chips","connect","refresh","read","compare","save"})
                Check(!((Control)Field(name)!).Enabled,name+" blocked during read/compare");
            Check(!((MenuStrip)Field("menu")!).Enabled && !((ToolStripMenuItem)Field("fileOpen")!).Enabled,"Open and menu blocked during operation");
            Check(grid.Enabled,"HEX remains readable during operation");
            Check(((Label)Field("stateLabel")!).Text=="Считывание","reading status shown while controls are blocked");
        }
        Task Read(byte[] bytes,bool corrupt=false,bool failRead=false) {
            var link=new Link(bytes,corrupt,failRead);
            var chip=new RomChip { Name="TestROM",Size=bytes.Length,Bus="parallel8",Pins="27C512" };
            Task task=(Task)Call("ReadDevice",link,chip,true)!;
            Locks();
            return CheckCommands(task,link,bytes.Length);
        }
        async Task CheckCommands(Task task,Link link,int size) {
            await task;
            Check(link.Writes.SequenceEqual(new[] {"PINS:27C512\n","READ:"+size+"\n"}),"Compare performs fresh pin selection and physical read command");
        }
        form.Shown+=async (_,_)=> {
            try {
                Check(typeof(MainForm).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion.Split('+')[0]=="1.2","version 1.2");
                var root=(TableLayoutPanel)form.Controls[0];
                var footer=(TableLayoutPanel)root.GetControlFromPosition(0,4)!;
                Check(root.RowStyles[4].Height==22 && footer.RowCount==1 && footer.Controls.Count==3 && footer.Controls.OfType<Label>().Any(c=>c.Text=="|"),"compact footer contains only device, separator and status");
                Check(((Label)Field("stateLabel")!).Text=="Не подключен" && ((Label)Field("deviceInfo")!).Text.Length==0,"initial disconnected status and empty device identity");
                Check(((Label)Field("detail")!).Text.Contains("65 536 байт (64КиБ/512КБит)"),"NM27C512 size includes bytes, KiB and Kbits");
                foreach(var item in new[] {(DumperStatus.Writing,"Запись"),(DumperStatus.Erasing,"Стирание"),(DumperStatus.Error,"Ошибка записи")}) {
                    Call("SetStatus",item.Item1,item.Item1==DumperStatus.Error ? "записи" : "","");
                    Check(((Label)Field("stateLabel")!).Text==item.Item2,"future programmer status "+item.Item2);
                }
                Call("Disconnect");
                Check(((ToolStripMenuItem)Field("fileOpen")!).ShortcutKeys==(Keys.Control|Keys.O),"File Open shortcut");
                Check(!((Control)Field("compare")!).Enabled,"Compare disabled without reference or connection");
                var file=Enumerable.Repeat((byte)0xff,48).ToArray();
                Call("SetReference","fixture.bin",file);
                Check((byte[])Field("data")! == file && grid.RowCount==3 && !(bool)Field("verified")!,"opened raw bytes displayed without pretending to be verified ROM");
                Type serial=typeof(MainForm).Assembly.GetType("EpromDumper.SerialLink")!;
                using(var closedPort=(IDisposable)Activator.CreateInstance(serial,"COM9999")!) {
                    typeof(MainForm).GetField("link",BindingFlags.Instance|BindingFlags.NonPublic)!.SetValue(form,closedPort);
                    Call("UpdateControls");
                    Check(((Control)Field("compare")!).Enabled,"Compare becomes available with loaded file and connection");
                    typeof(MainForm).GetField("link",BindingFlags.Instance|BindingFlags.NonPublic)!.SetValue(form,null);
                    Call("UpdateControls");
                }
                var rom=(byte[])file.Clone(); rom[19]=0x7f; rom[32]=0x00; rom[47]=0xfe;
                await Read(rom);
                Check(((Label)Field("stateLabel")!).Text=="Готов","completed read returns to ready");
                var result=(RomComparison)Field("comparison")!;
                Check(result.Count==3 && result.FirstAddress==19 && result.LastAddress==47,"complete ROM comparison results");
                Check(grid.CurrentCell!.RowIndex==1 && grid.CurrentCell.ColumnIndex==4 && grid.SelectedCells.Count==1,"cursor and only selection remain on first mismatch");
                Check(grid.CurrentCell.Displayed,"first mismatch is visible in short image");
                FormatCells(48);
                foreach(int address in new[] {19,32,47}) {
                    var style=styles[address];
                    Check(style.Back.R>style.Back.G && style.Fore==Color.White && style.SelectedBack==style.Back && style.SelectedFore==Color.White,"red background and white text including selected byte "+address);
                }
                Check(styles[18].Back==Color.White && styles[18].Fore==Color.Black,"matching byte keeps normal style");
                Check(messages.Count==1 && messages[0].Icon==MessageBoxIcon.Warning && messages[0].Text.Contains("7F:00000013") && messages[0].Text.Contains("FE:0000002F") && messages[0].Text.Contains("байтов: 3"),"mismatch message includes first/last ROM byte, address and total");
                var tip=(RomDifference)Call("DifferenceAt",19)!;
                Check(tip.Address==19 && tip.FileHex=="FF" && tip.RomHex=="7F" && tip.BitMask==128,"hover obtains exact file and ROM bytes for differing cell");
                Call("HoverCell",1,4); Check((int)Field("hoverAddress")! ==19,"hover targets first mismatch");
                Call("HoverCell",1,3); Check((int)Field("hoverAddress")! ==-1,"matching cell hides difference tooltip");
                if(args.Length>0) {
                    Directory.CreateDirectory(args[0]);
                    using(var image=new Bitmap(form.Width,form.Height)) {
                        form.DrawToBitmap(image,new Rectangle(0,0,form.Width,form.Height));
                        image.Save(Path.Combine(args[0],"comparison-ui.png"));
                    }
                    using var tooltip=new Bitmap(DifferenceToolTip.GetSize().Width,DifferenceToolTip.GetSize().Height); using var graphics=Graphics.FromImage(tooltip);
                    DifferenceToolTip.Paint(graphics,tooltip.Size,new RomDifference(0x000c137e,0xa1,0x25));
                    tooltip.Save(Path.Combine(args[0],"difference-tooltip.png"));
                }
                messages.Clear(); await Read(file);
                Check(((RomComparison)Field("comparison")!).Identical && messages.Count==1 && messages[0].Icon==MessageBoxIcon.Information && messages[0].Text=="Содержимое ROM идентично загруженному файлу.","identical verified read shows success");
                FormatCells(48); Check(styles[19].Back==Color.White,"new comparison clears previous red highlights");
                Check(((Control)Field("save")!).Enabled,"verified read can be saved");
                var large=Enumerable.Repeat((byte)0xff,65536).ToArray();
                Call("SetReference","last-byte.bin",large);
                var largeRom=(byte[])large.Clone(); largeRom[65535]=0x7f;
                messages.Clear(); await Read(largeRom);
                Check(((RomComparison)Field("comparison")!).FirstAddress==65535 && grid.CurrentCell!.RowIndex==4095 && grid.CurrentCell.ColumnIndex==16 && grid.CurrentCell.Displayed && grid.FirstDisplayedScrollingRowIndex>0,"64 KiB image scrolls to last-byte mismatch and focuses its exact cell");
                Call("SetReference","longer.img",Enumerable.Repeat((byte)0xff,18).ToArray());
                messages.Clear(); await Read(Enumerable.Repeat((byte)0xff,16).ToArray());
                result=(RomComparison)Field("comparison")!;
                Check(result.Count==2 && grid.RowCount==2 && grid.CurrentCell!.RowIndex==1 && grid.CurrentCell.ColumnIndex==1,"file tail is visible, counted and selected");
                Check(grid.Rows[1].Cells[1].FormattedValue?.ToString()=="—" && messages[0].Text.Contains("—:00000010"),"missing ROM byte displayed and reported explicitly");
                Call("SetReference","shorter.rom",new byte[] {0xff});
                messages.Clear(); await Read(new byte[] {0xff,0xa5,0xfe});
                Check(((RomComparison)Field("comparison")!).Count==2 && ((RomDifference)Call("DifferenceAt",1)!).FileHex=="—","ROM tail missing in file is compared");
                Call("SetReference","crc.dump",new byte[] {1,2,3,4});
                messages.Clear(); await Read(new byte[] {1,2,3,4},true);
                Check(Field("comparison")==null && !(bool)Field("verified")! && !((Control)Field("save")!).Enabled && messages.Count==1 && messages[0].Icon==MessageBoxIcon.Error && messages[0].Text.Contains("CRC"),"CRC failure cannot produce successful compare or save");
                Check(((byte[])Field("referenceData")!).SequenceEqual(new byte[] {1,2,3,4}),"reference retained after failed read");
                Check(((Control)Field("chips")!).Enabled && ((Control)Field("ports")!).Enabled && ((ToolStripMenuItem)Field("fileOpen")!).Enabled,"controls unlock after error");
                Check(((Label)Field("stateLabel")!).Text=="Ошибка данных CRC" && Field("link")==null && ((Label)Field("deviceInfo")!).Text.Length==0,"CRC error remains visible after disconnect and controls unlock");
                messages.Clear(); await Read(new byte[] {1,2,3,4},failRead:true);
                Check(((Label)Field("stateLabel")!).Text=="Ошибка чтения ROM" && !(bool)Field("verified")! && messages.Count==1,"read interruption has its own persistent error status");
                Call("SetReference","recovery.bin",new byte[] {1,2,3,4});
                Check(((Label)Field("stateLabel")!).Text=="Не подключен","opening a file does not report a disconnected device as ready");
                Console.WriteLine(passed+" UI checks passed; device link simulated, no real COM port opened.");
            } catch(Exception ex) { Console.Error.WriteLine(ex); Environment.ExitCode=1; }
            finally { form.Close(); }
        };
        Application.Run(form);
    }
}
