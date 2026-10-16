using System;
using System.Drawing;
using System.Drawing.Text;
using System.Windows.Forms;
using EpromDumper.Core;
namespace EpromDumper;

public sealed class DifferenceToolTip : ToolTip {
    private RomDifference difference;
    private float scale=1;
    public DifferenceToolTip() {
        OwnerDraw=true; UseAnimation=false; UseFading=false;
        Popup+=(_,e)=>e.ToolTipSize=GetSize(scale);
        Draw+=(_,e)=>Paint(e.Graphics,e.Bounds.Size,difference,scale);
    }
    public void ShowDifference(Control owner,Point point,RomDifference value) {
        Hide(owner); difference=value; scale=owner.DeviceDpi/96f;
        Show(value.Address.ToString("X8"),owner,point,15000);
    }
    public static Size GetSize(float scale=1) => new((int)Math.Ceiling(260*scale),(int)Math.Ceiling(86*scale));
    public static void Paint(Graphics graphics,Size size,RomDifference value,float scale=1) {
        int P(float pixels)=>(int)Math.Round(pixels*scale);
        graphics.Clear(Color.FromArgb(255,255,246));
        using var border=new Pen(Color.FromArgb(118,130,149));
        graphics.DrawRectangle(border,0,0,size.Width-1,size.Height-1);
        using var label=new Font("Segoe UI",14*scale,FontStyle.Regular,GraphicsUnit.Pixel);
        using var bold=new Font("Consolas",17*scale,FontStyle.Bold,GraphicsUnit.Pixel);
        using var mono=new Font("Consolas",17*scale,FontStyle.Regular,GraphicsUnit.Pixel);
        using var format=(StringFormat)StringFormat.GenericTypographic.Clone();
        format.FormatFlags|=StringFormatFlags.NoWrap;
        graphics.TextRenderingHint=TextRenderingHint.AntiAliasGridFit;
        Color normal=Color.FromArgb(25,33,48), changed=Color.FromArgb(204,25,45);
        void Text(string text,Font font,int x,int y,Color color) {
            using var brush=new SolidBrush(color);
            graphics.DrawString(text,font,brush,new PointF(P(x),P(y)),format);
        }
        Text("Адрес:",label,10,8,normal); Text(value.Address.ToString("X8"),bold,78,6,normal);
        void Row(string caption,string hex,string binary,int y) {
            Text(caption,label,10,y+1,normal);
            if(hex=="—") Text(hex,mono,78,y,changed);
            else for(int i=0;i<2;i++) Text(hex[i].ToString(),mono,78+i*13,y,(value.BitMask&(i==0?240:15))!=0?changed:normal);
            for(int i=0;i<8;i++) Text(binary[i].ToString(),mono,126+i*13+(i>=4?6:0),y,(value.BitMask&(1<<(7-i)))!=0?changed:normal);
        }
        Row("Файл:",value.FileHex,value.FileBinary,31);
        Row("ROM:",value.RomHex,value.RomBinary,56);
    }
}
