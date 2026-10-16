using System;
using System.Windows.Forms;
namespace EpromDumper;
internal static class Program {
    [STAThread] static void Main(string[] args) {
        ApplicationConfiguration.Initialize();
        Application.Run(Array.IndexOf(args,"--about")>=0 ? new AboutForm(args) : new MainForm(args));
    }
}
