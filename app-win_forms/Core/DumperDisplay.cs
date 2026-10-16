using System.Globalization;
namespace EpromDumper.Core;

public enum DumperStatus { NotConnected, Ready, Reading, Writing, Erasing, Error }

public static class DumperDisplay {
    private static readonly NumberFormatInfo numbers=new() { NumberGroupSeparator=" ", NumberDecimalSeparator=",", NumberGroupSizes=new[] {3} };
    public static string Size(int bytes) => bytes.ToString("N0",numbers)+" байт ("+
        (bytes/1024m).ToString("0.###",numbers)+"КиБ/"+(bytes/128m).ToString("0.###",numbers)+"КБит)";
    public static string Status(DumperStatus status,string error="") => status switch {
        DumperStatus.Ready=>"Готов",
        DumperStatus.Reading=>"Считывание",
        DumperStatus.Writing=>"Запись",
        DumperStatus.Erasing=>"Стирание",
        DumperStatus.Error=>error.Length==0 ? "Ошибка" : "Ошибка "+error,
        _=>"Не подключен"
    };
}
