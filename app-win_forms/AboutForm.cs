using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
namespace EpromDumper;
public sealed class AboutForm : Form {
    private readonly Image logo;
    private System.Windows.Forms.Timer? renderTimer;
    public AboutForm(string[]? args=null) {
        Text="О программе — "+ApplicationInfo.Name;
        StartPosition=FormStartPosition.CenterParent; ClientSize=new Size(600,255);
        FormBorderStyle=FormBorderStyle.FixedDialog; MaximizeBox=false; MinimizeBox=false; ShowInTaskbar=false;
        Font=new Font("Segoe UI",10); BackColor=Color.FromArgb(244,247,251); AutoScaleMode=AutoScaleMode.Dpi;
        using(var stream=typeof(AboutForm).Assembly.GetManifestResourceStream("LunarView3.Logo.png")!)
        using(var original=Image.FromStream(stream)) logo=new Bitmap(original);
        var layout=new TableLayoutPanel { Dock=DockStyle.Fill, Padding=new Padding(12), ColumnCount=2, RowCount=4 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,180)); layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute,44)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute,66));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize)); layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        var picture=new PictureBox { Image=logo, SizeMode=PictureBoxSizeMode.Zoom, Dock=DockStyle.Fill, Margin=new Padding(0,0,12,0), TabStop=false };
        layout.Controls.Add(picture,0,0); layout.SetRowSpan(picture,3);
        layout.Controls.Add(new Label { Text=ApplicationInfo.Name, Font=new Font("Segoe UI",20,FontStyle.Bold), Dock=DockStyle.Fill, TextAlign=ContentAlignment.MiddleLeft },1,0);
        layout.Controls.Add(new Label { Text="Версия: "+ApplicationInfo.Version+"\nРазработчик: "+ApplicationInfo.Developer+"\nДата сборки: "+ApplicationInfo.BuildDate, Dock=DockStyle.Fill, TextAlign=ContentAlignment.MiddleLeft },1,1);
        layout.Controls.Add(new Label { Text=ApplicationInfo.Description, AutoSize=true, Dock=DockStyle.Top, Margin=new Padding(3,4,3,0) },1,2);
        var close=new Button { Text="Закрыть", DialogResult=DialogResult.Cancel, Width=96, Height=30, Anchor=AnchorStyles.Left|AnchorStyles.Top, Margin=new Padding(3,8,0,0) };
        layout.Controls.Add(close,1,3); Controls.Add(layout); AcceptButton=close; CancelButton=close;
        if(args!=null) {
            int index=Array.IndexOf(args,"--render");
            if(index>=0 && index+1<args.Length) Shown+=(_,_)=> {
                renderTimer=new System.Windows.Forms.Timer { Interval=500 };
                renderTimer.Tick+=(_,_)=> {
                    renderTimer.Stop();
                    using var image=new Bitmap(Width,Height); DrawToBitmap(image,new Rectangle(0,0,Width,Height));
                    image.Save(Path.GetFullPath(args[index+1]),System.Drawing.Imaging.ImageFormat.Png); Close();
                };
                renderTimer.Start();
            };
        }
    }
    protected override void Dispose(bool disposing) {
        if(disposing) { renderTimer?.Dispose(); logo.Dispose(); }
        base.Dispose(disposing);
    }
}
