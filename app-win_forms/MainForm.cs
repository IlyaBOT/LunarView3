using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.IO.Ports;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using EpromDumper.Core;
namespace EpromDumper;
public sealed class MainForm : Form {
    private readonly MenuStrip menu=new() { Dock=DockStyle.Fill, Padding=Padding.Empty };
    private readonly ToolStripMenuItem fileOpen=new("Открыть…") { ShortcutKeys=Keys.Control|Keys.O };
    private readonly ToolStripMenuItem fileSave=new("Сохранить BIN…") { ShortcutKeys=Keys.Control|Keys.S };
    private readonly ComboBox ports=new() { DropDownStyle=ComboBoxStyle.DropDownList, Width=90 };
    private readonly ComboBox chips=new() { DropDownStyle=ComboBoxStyle.DropDownList, Width=195 };
    private readonly Button connect=new() { Text="Подключиться", Width=112, Height=28 };
    private readonly Button refresh=new() { Text="↻", Width=26, Height=28, AccessibleName="Обновить COM-порты" };
    private readonly Button read=new() { Text="Читать", Width=72, Height=28 };
    private readonly Button compare=new() { Text="Сравнить", Width=80, Height=28 };
    private readonly Button save=new() { Text="Сохранить BIN", Width=114, Height=28 };
    private readonly Label detail=new() { AutoEllipsis=true, Dock=DockStyle.Fill, TextAlign=ContentAlignment.MiddleLeft, Margin=Padding.Empty };
    private readonly Label stateLabel=new() { Text="Не подключен", AutoSize=true, Dock=DockStyle.Fill, TextAlign=ContentAlignment.MiddleLeft, Margin=Padding.Empty };
    private readonly Label deviceInfo=new() { Dock=DockStyle.Fill, TextAlign=ContentAlignment.MiddleLeft, AutoEllipsis=true, Margin=Padding.Empty };
    private readonly DataGridView grid=new() {
        Dock=DockStyle.Fill, VirtualMode=true, ReadOnly=true, AllowUserToAddRows=false, AllowUserToDeleteRows=false,
        AllowUserToResizeRows=false, RowHeadersVisible=false, MultiSelect=false, SelectionMode=DataGridViewSelectionMode.CellSelect,
        BackgroundColor=Color.White, BorderStyle=BorderStyle.FixedSingle, CellBorderStyle=DataGridViewCellBorderStyle.None,
        AutoGenerateColumns=false, EnableHeadersVisualStyles=false, Margin=Padding.Empty
    };
    private byte[] data=Array.Empty<byte>();
    private byte[]? referenceData;
    private string referencePath="";
    private RomComparison? comparison;
    private readonly DifferenceToolTip differenceTip=new();
    private readonly System.Windows.Forms.Timer hoverTimer=new() { Interval=350 };
    private int hoverAddress=-1;
    private readonly Action<string,string,MessageBoxIcon> notify;
    private int available;
    private bool busy, verified, closeRequested;
    private SerialLink? link;
    private CancellationTokenSource? cancel;
    private string dumpName="rom";
    private readonly ToolTip tips=new();
    public MainForm(string[] args,Action<string,string,MessageBoxIcon>? notification=null) {
        notify=notification ?? ((message,title,icon)=>MessageBox.Show(this,message,title,MessageBoxButtons.OK,icon));
        Text=ApplicationInfo.Name; Name="LunarView3MainForm";
        StartPosition=FormStartPosition.CenterScreen; MinimumSize=new Size(890,480); Size=new Size(890,690);
        Font=new Font("Segoe UI",9); BackColor=Color.FromArgb(244,247,251); AutoScaleMode=AutoScaleMode.Dpi;
        var root=new TableLayoutPanel { Dock=DockStyle.Fill, Padding=new Padding(4), ColumnCount=1, RowCount=5 };
        root.RowStyles.Add(new RowStyle(SizeType.Absolute,22));
        root.RowStyles.Add(new RowStyle(SizeType.Absolute,32));
        root.RowStyles.Add(new RowStyle(SizeType.Absolute,22));
        root.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        root.RowStyles.Add(new RowStyle(SizeType.Absolute,22));
        var file=new ToolStripMenuItem("&Файл");
        var exit=new ToolStripMenuItem("Выход") { ShortcutKeys=Keys.Alt|Keys.F4 };
        fileOpen.Click+=async (_,_)=>await OpenRom();
        fileSave.Click+=(_,_)=>SaveDump(); exit.Click+=(_,_)=>Close();
        file.DropDownItems.AddRange(new ToolStripItem[] { fileOpen,fileSave,new ToolStripSeparator(),exit });
        var help=new ToolStripMenuItem("&Справка");
        var about=new ToolStripMenuItem("О программе…") { ShortcutKeys=Keys.F1 };
        about.Click+=(_,_)=> { using var dialog=new AboutForm(); dialog.ShowDialog(this); };
        help.DropDownItems.Add(about); menu.Items.AddRange(new ToolStripItem[] { file,help });
        menu.BackColor=BackColor; menu.Margin=Padding.Empty; MainMenuStrip=menu; root.Controls.Add(menu,0,0);
        var bar=new FlowLayoutPanel { Dock=DockStyle.Fill, WrapContents=false, AutoScroll=true, Margin=Padding.Empty };
        Label Caption(string t) => new() { Text=t, AutoSize=true, Margin=new Padding(0,6,3,0) };
        ports.Margin=new Padding(0,3,3,0); chips.Margin=new Padding(0,3,4,0);
        connect.Margin=new Padding(0,0,5,0); refresh.Margin=new Padding(0,0,3,0);
        read.Margin=new Padding(0,0,3,0); compare.Margin=new Padding(0,0,3,0); save.Margin=Padding.Empty;
        bar.Controls.AddRange(new Control[] { Caption("COM-порт:"),ports,refresh,connect,Caption("Микросхема:"),chips,read,compare,save });
        root.Controls.Add(bar,0,1); root.Controls.Add(detail,0,2); root.Controls.Add(grid,0,3);
        var footer=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=3, RowCount=1, Margin=Padding.Empty };
        footer.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
        footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,16));
        footer.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        footer.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        var separator=new Label { Text="|", Dock=DockStyle.Fill, TextAlign=ContentAlignment.MiddleCenter, Margin=Padding.Empty };
        footer.Controls.Add(deviceInfo,0,0); footer.Controls.Add(separator,1,0); footer.Controls.Add(stateLabel,2,0);
        root.Controls.Add(footer,0,4); Controls.Add(root);
        grid.DefaultCellStyle.Font=new Font("Consolas",11);
        grid.DefaultCellStyle.SelectionBackColor=Color.FromArgb(220,234,252); grid.DefaultCellStyle.SelectionForeColor=Color.Black;
        grid.ColumnHeadersDefaultCellStyle.BackColor=Color.FromArgb(234,239,246);
        grid.ColumnHeadersDefaultCellStyle.Font=new Font("Consolas",10); grid.ColumnHeadersHeight=29; grid.RowTemplate.Height=23;
        grid.Columns.Add(new DataGridViewTextBoxColumn { Name="Address", HeaderText="Адрес", Width=92, Frozen=true, SortMode=DataGridViewColumnSortMode.NotSortable, DefaultCellStyle=new DataGridViewCellStyle { ForeColor=Color.Blue, Padding=new Padding(3,0,0,0) } });
        for(int i=0;i<16;i++) grid.Columns.Add(new DataGridViewTextBoxColumn { Name="B"+i, HeaderText=i.ToString("X2"), Width=34, SortMode=DataGridViewColumnSortMode.NotSortable });
        grid.Columns.Add(new DataGridViewTextBoxColumn { Name="Ascii", HeaderText="ASCII", Width=220, AutoSizeMode=DataGridViewAutoSizeColumnMode.Fill, MinimumWidth=205, SortMode=DataGridViewColumnSortMode.NotSortable });
        grid.CellValueNeeded+=GridValue;
        grid.CellFormatting+=GridFormatting;
        grid.ShowCellToolTips=false;
        grid.CellMouseEnter+=(_,e)=>HoverCell(e.RowIndex,e.ColumnIndex);
        grid.CellMouseLeave+=(_,_)=>HideDifferenceTip();
        grid.MouseLeave+=(_,_)=>HideDifferenceTip();
        grid.Scroll+=(_,_)=>HideDifferenceTip();
        grid.MouseDown+=(_,_)=>HideDifferenceTip();
        hoverTimer.Tick+=(_,_)=> {
            hoverTimer.Stop();
            if(hoverAddress<0 || comparison?.IsDifferent(hoverAddress)!=true) return;
            Point mouse=grid.PointToClient(Cursor.Position);
            var hit=grid.HitTest(mouse.X,mouse.Y);
            if(hit.RowIndex<0 || hit.ColumnIndex<1 || hit.ColumnIndex>16 || hit.RowIndex*16+hit.ColumnIndex-1!=hoverAddress) return;
            differenceTip.ShowDifference(grid,new Point(mouse.X+14,mouse.Y+20),DifferenceAt(hoverAddress));
        };
        connect.Click+=async (_,_) => await ToggleConnection();
        read.Click+=async (_,_) => await ReadRom(); refresh.Click+=(_,_) => RefreshPorts(); save.Click+=(_,_) => SaveDump();
        compare.Click+=async (_,_)=>await ReadRom(true);
        chips.SelectedIndexChanged+=(_,_) => { DescribeChip(); UpdateControls(); };
        ports.DropDown+=(_,_) => { if(!busy && link==null) RefreshPorts(); };
        FormClosing+=async (_,e) => {
            if(busy) { e.Cancel=true; closeRequested=true; cancel?.Cancel(); }
            else if(link!=null) { e.Cancel=true; closeRequested=true; await StopAndDisconnect(); }
        };
        Shown+=(_,_) => {
            try {
                chips.DataSource=ChipCatalog.Load(Path.Combine(AppContext.BaseDirectory,"rom-chips.list")).ToList();
                RefreshPorts(); DescribeChip(); UpdateControls();
                if(args.Contains("--demo")) Demo();
                if(args.Contains("--demo-compare")) DemoComparison();
                int index=Array.IndexOf(args,"--render");
                if(index>=0 && index+1<args.Length) {
                    var timer=new System.Windows.Forms.Timer { Interval=500 };
                    timer.Tick+=(_,_) => {
                        timer.Stop();
                        using var image=new Bitmap(Width,Height); DrawToBitmap(image,new Rectangle(0,0,Width,Height));
                        image.Save(Path.GetFullPath(args[index+1]),System.Drawing.Imaging.ImageFormat.Png); Close();
                    }; timer.Start(); // Keep the timer alive until this form is disposed.
                    renderTimer=timer;
                }
            } catch(Exception ex) { SetStatus(DumperStatus.Error,"загрузки списка микросхем",ex.Message); notify(ex.Message,"Ошибка каталога",MessageBoxIcon.Error); UpdateControls(); }
        };
        UpdateControls();
    }
    private System.Windows.Forms.Timer? renderTimer;
    private RomChip? SelectedChip => chips.SelectedItem as RomChip;
    private void RefreshPorts() {
        string previous=ports.SelectedItem as string ?? "";
        var names=SerialPort.GetPortNames().OrderBy(s=>int.TryParse(s.AsSpan(3),out int n)?n:int.MaxValue).ToArray();
        ports.Items.Clear(); ports.Items.AddRange(names);
        if(names.Contains(previous)) ports.SelectedItem=previous; else if(names.Length>0) ports.SelectedIndex=0;
    }
    private void DescribeChip() {
        var chip=SelectedChip;
        var parts=new List<string>();
        if(chip!=null) {
            parts.Add(DumperDisplay.Size(chip.Size)); parts.Add(chip.Vcc.ToString("0.0",CultureInfo.InvariantCulture)+" В");
            parts.Add(chip.Adapter.Length==0 ? "Адаптер не требуется" : chip.Adapter);
            if(chip.Comment.Length>0) parts.Add(chip.Comment);
        }
        if(referenceData!=null) parts.Add($"Файл: {Path.GetFileName(referencePath)} — {DumperDisplay.Size(referenceData.Length)}");
        detail.Text=string.Join(" · ",parts);
        tips.SetToolTip(detail,detail.Text+(referenceData!=null ? "\n"+referencePath : "")+(chip?.Supported==false ? "\n"+chip.BlockReason : ""));
    }
    private void UpdateControls() {
        ports.Enabled=!busy && link==null; refresh.Enabled=!busy && link==null;
        chips.Enabled=!busy; connect.Enabled=!busy && (link!=null || ports.Items.Count>0);
        connect.Text=link==null?"Подключиться":"Отключиться";
        read.Enabled=!busy && link!=null && SelectedChip?.Supported==true;
        compare.Enabled=read.Enabled && referenceData!=null;
        save.Enabled=!busy && verified; grid.Enabled=true;
        menu.Enabled=!busy; fileOpen.Enabled=!busy; fileSave.Enabled=save.Enabled;
    }
    private void StartWork() { busy=true; cancel=new CancellationTokenSource(); UpdateControls(); }
    private void EndWork() { busy=false; cancel?.Dispose(); cancel=null; UpdateControls(); if(closeRequested) BeginInvoke(new Action(Close)); }
    private void SetStatus(DumperStatus status,string error="",string explanation="") {
        stateLabel.Text=DumperDisplay.Status(status,error);
        stateLabel.ForeColor=status==DumperStatus.Error ? Color.FromArgb(190,25,35) : SystemColors.ControlText;
        tips.SetToolTip(stateLabel,explanation.Length>0 ? explanation : stateLabel.Text);
    }
    private void SetIdleStatus() => SetStatus(link==null ? DumperStatus.NotConnected : DumperStatus.Ready);
    private void Disconnect() {
        link?.Dispose(); link=null; SetStatus(DumperStatus.NotConnected); deviceInfo.Text=""; tips.SetToolTip(deviceInfo,""); UpdateControls();
    }
    private async Task StopAndDisconnect() {
        if(link==null || busy) return;
        StartWork(); var opened=link;
        try { await Task.Run(()=>DumperSession.Stop(opened,cancel!.Token)); Disconnect(); }
        catch(OperationCanceledException) { Disconnect(); }
        catch(Exception ex) { Disconnect(); SetStatus(DumperStatus.Error,"отключения от программатора",ex.Message); }
        finally { EndWork(); }
    }
    private async Task ToggleConnection() {
        if(busy) return;
        if(link!=null) { await StopAndDisconnect(); return; }
        if(ports.SelectedItem is not string portName) return;
        StartWork(); SetStatus(DumperStatus.NotConnected);
        var opened=new SerialLink(portName);
        try {
            string identity=await Task.Run(()=> { opened.Open(); return DumperSession.Handshake(opened,cancel!.Token); });
            link=opened; deviceInfo.Text=identity; tips.SetToolTip(deviceInfo,identity); SetStatus(DumperStatus.Ready);
        } catch(OperationCanceledException) { opened.Dispose(); SetStatus(DumperStatus.NotConnected); }
        catch(Exception ex) { opened.Dispose(); SetStatus(DumperStatus.Error,"подключения к программатору",ex.Message); if(!closeRequested) notify(ex.Message,"Подключение",MessageBoxIcon.Error); }
        finally { EndWork(); }
    }
    private async Task ReadRom(bool compareFile=false) {
        if(busy || link==null || SelectedChip is not RomChip chip || !chip.Supported) return;
        await ReadDevice(link,chip,compareFile);
    }
    private async Task ReadDevice(IDeviceLink port,RomChip chip,bool compareFile) {
        if(busy || (compareFile && referenceData==null)) return;
        StartWork(); verified=false; dumpName=chip.Name; ClearComparison();
        var parser=new DumpParser(chip.Size); data=parser.Buffer; available=0;
        grid.RowCount=(chip.Size+15)/16; grid.Invalidate();
        var notifier=new Progress<int>(n=> {
            if(!busy || verified || !ReferenceEquals(data,parser.Buffer)) return;
            available=n; grid.Invalidate();
        });
        try {
            SetStatus(DumperStatus.Reading);
            await Task.Run(()=> {
                DumperSession.SelectPins(port,chip.Pins,cancel!.Token);
                DumperSession.Read(port,parser,n=>((IProgress<int>)notifier).Report(n),cancel!.Token);
            });
            available=chip.Size; verified=true; grid.Invalidate();
            if(compareFile) {
                comparison=await Task.Run(()=>new RomComparison(referenceData!,data));
                ApplyComparison();
                SetStatus(DumperStatus.Ready);
                if(!closeRequested) {
                    if(comparison.Identical) notify("Содержимое ROM идентично загруженному файлу.","Сравнение ROM",MessageBoxIcon.Information);
                    else notify(ComparisonMessage(),"Сравнение ROM",MessageBoxIcon.Warning);
                }
            } else SetStatus(DumperStatus.Ready);
        } catch(OperationCanceledException) { Disconnect(); }
        catch(Exception ex) {
            Disconnect();
            SetStatus(DumperStatus.Error,ex is InvalidDataException && ex.Message.StartsWith("Ошибка CRC:",StringComparison.Ordinal) ? "данных CRC" : "чтения ROM",ex.Message);
            if(!closeRequested) notify(ex.Message+"\nНеполный дамп сохранять нельзя. Подключитесь заново.","Ошибка чтения",MessageBoxIcon.Error);
        } finally { EndWork(); }
    }
    private async Task OpenRom() {
        if(busy) return;
        using var dialog=new OpenFileDialog { Title="Открыть ROM-файл", Filter="ROM-файлы (*.bin;*.img;*.rom;*.dump)|*.bin;*.img;*.rom;*.dump|BIN (*.bin)|*.bin|IMG (*.img)|*.img|ROM (*.rom)|*.rom|DUMP (*.dump)|*.dump", CheckFileExists=true, Multiselect=false };
        if(dialog.ShowDialog(this)!=DialogResult.OK) return;
        StartWork();
        try {
            byte[] bytes=await Task.Run(()=>RomFile.Load(dialog.FileName));
            SetReference(dialog.FileName,bytes);
        } catch(Exception ex) { SetStatus(DumperStatus.Error,"открытия ROM-файла",ex.Message); if(!closeRequested) notify(ex.Message,"Открытие ROM-файла",MessageBoxIcon.Error); }
        finally { EndWork(); }
    }
    private void SetReference(string path,byte[] bytes) {
        ClearComparison(); referenceData=bytes; referencePath=path;
        data=bytes; available=bytes.Length; verified=false; dumpName=Path.GetFileNameWithoutExtension(path);
        grid.RowCount=(data.Length+15)/16; grid.ClearSelection();
        if(grid.RowCount>0) { grid.CurrentCell=grid.Rows[0].Cells[1]; grid.FirstDisplayedScrollingRowIndex=0; }
        SetIdleStatus();
        grid.Invalidate(); DescribeChip(); UpdateControls();
    }
    private void ClearComparison() { HideDifferenceTip(); comparison=null; grid.Invalidate(); }
    private RomDifference DifferenceAt(int address) => new(address,
        referenceData!=null && address<referenceData.Length ? referenceData[address] : null,
        address<available ? data[address] : null);
    private void ApplyComparison() {
        if(comparison==null) return;
        grid.RowCount=(comparison.Length+15)/16;
        grid.ClearSelection();
        if(!comparison.Identical) {
            int address=comparison.FirstAddress;
            grid.CurrentCell=grid.Rows[address/16].Cells[address%16+1];
            grid.FirstDisplayedScrollingRowIndex=address/16; grid.Focus();
        }
        grid.Invalidate();
    }
    private string ComparisonMessage() {
        var first=DifferenceAt(comparison!.FirstAddress); var last=DifferenceAt(comparison.LastAddress);
        string message=$"Содержимое ROM отличается от загруженного файла.\n\nПервый различающийся байт: {first.RomHex}:{first.Address:X8}\nПоследний различающийся байт: {last.RomHex}:{last.Address:X8}\nВсего отличающихся байтов: {comparison.Count:N0}";
        if(comparison.FileLength!=comparison.RomLength) message+=$"\n\nРазмер файла: {comparison.FileLength:N0} байт; размер ROM: {comparison.RomLength:N0} байт.\n«—» означает отсутствующий байт; лишние байты тоже посчитаны отличиями.";
        return message;
    }
    private void GridFormatting(object? sender,DataGridViewCellFormattingEventArgs e) {
        if(e.RowIndex<0 || e.ColumnIndex<1 || e.ColumnIndex>16 || e.CellStyle is not DataGridViewCellStyle style) return;
        bool different=comparison?.IsDifferent(e.RowIndex*16+e.ColumnIndex-1)==true;
        style.BackColor=different ? Color.FromArgb(206,32,46) : Color.White;
        style.ForeColor=different ? Color.White : Color.Black;
        style.SelectionBackColor=different ? Color.FromArgb(206,32,46) : grid.DefaultCellStyle.SelectionBackColor;
        style.SelectionForeColor=different ? Color.White : grid.DefaultCellStyle.SelectionForeColor;
    }
    private void HoverCell(int row,int column) {
        HideDifferenceTip();
        if(row<0 || column<1 || column>16) return;
        int address=row*16+column-1;
        if(comparison?.IsDifferent(address)!=true) return;
        hoverAddress=address; hoverTimer.Start();
    }
    private void HideDifferenceTip() { hoverTimer.Stop(); hoverAddress=-1; differenceTip.Hide(grid); }
    private void SaveDump() {
        if(busy || !verified) return;
        using var dialog=new SaveFileDialog { Filter="Двоичный дамп (*.bin)|*.bin|Все файлы (*.*)|*.*", FileName=dumpName+".bin", OverwritePrompt=true };
        if(dialog.ShowDialog(this)!=DialogResult.OK) return;
        try { File.WriteAllBytes(dialog.FileName,data); SetIdleStatus(); }
        catch(Exception ex) { SetStatus(DumperStatus.Error,"сохранения ROM-файла",ex.Message); notify(ex.Message,"Сохранение",MessageBoxIcon.Error); }
    }
    private void GridValue(object? sender,DataGridViewCellValueEventArgs e) {
        int address=e.RowIndex*16;
        if(e.ColumnIndex==0) { e.Value=address.ToString("X8"); return; }
        if(e.ColumnIndex==17) {
            var chars=new char[16];
            for(int i=0;i<16;i++) chars[i]=address+i<available ? (data[address+i]>=32 && data[address+i]<=126 ? (char)data[address+i] : '.') : ' ';
            e.Value=new string(chars); return;
        }
        int offset=address+e.ColumnIndex-1;
        e.Value=offset<available ? data[offset].ToString("X2") : comparison?.IsDifferent(offset)==true ? "—" : "";
    }
    private void Demo() {
        ClearComparison();
        data=Enumerable.Repeat((byte)255,65536).ToArray();
        var head=new byte[] {255,255,160,21,238,238,193,0,19,55,66,0,255,255,255,255};
        Array.Copy(head,data,head.Length); var message=System.Text.Encoding.ASCII.GetBytes("EPROM DUMPER / DEMO"); Array.Copy(message,0,data,32,message.Length);
        available=data.Length; grid.RowCount=data.Length/16; verified=false;
        SetStatus(DumperStatus.NotConnected);
        deviceInfo.Text="Демо · Lunar Dumper (Rev. 1) | Firmware: v.1.0.0 (build demo) "+DateTime.Now.ToString("dd.MM.yyyy");
        tips.SetToolTip(deviceInfo,deviceInfo.Text); grid.Invalidate(); UpdateControls();
    }
    private void DemoComparison() {
        Demo(); referenceData=(byte[])data.Clone(); referencePath="comparison-demo.bin";
        data[2]^=1; data[47]^=128; data[65535]^=1;
        comparison=new RomComparison(referenceData,data); ApplyComparison(); DescribeChip();
    }
    protected override void Dispose(bool disposing) {
        if(disposing) { renderTimer?.Dispose(); hoverTimer.Dispose(); differenceTip.Dispose(); tips.Dispose(); }
        base.Dispose(disposing);
    }
}
