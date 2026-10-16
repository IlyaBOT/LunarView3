using System.Linq;
using System.Reflection;
namespace EpromDumper;
internal static class ApplicationInfo {
    private static readonly Assembly assembly=typeof(ApplicationInfo).Assembly;
    public static readonly string Name=assembly.GetCustomAttribute<AssemblyProductAttribute>()!.Product;
    public static readonly string Version=assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion.Split('+')[0];
    public static readonly string Developer=assembly.GetCustomAttribute<AssemblyCompanyAttribute>()!.Company;
    public static readonly string BuildDate=assembly.GetCustomAttributes<AssemblyMetadataAttribute>().Single(a=>a.Key=="BuildDate").Value!;
    public static readonly string Description=assembly.GetCustomAttribute<AssemblyDescriptionAttribute>()!.Description;
}
