using System.Runtime.InteropServices;
using System.Text;

namespace MDify.Windows.Support;

public enum PackageIdentityState
{
    Present,
    Absent,
    Unknown
}

public sealed record PackageIdentityResult(
    PackageIdentityState State,
    string? FullName,
    int ErrorCode);

public static class PackageIdentityProbe
{
    public const int ErrorSuccess = 0;
    public const int ErrorInsufficientBuffer = 122;
    public const int AppModelErrorNoPackage = 15700;

    public static PackageIdentityResult Probe()
    {
        uint length = 0;
        var result = GetCurrentPackageFullName(ref length, null);
        if (result == AppModelErrorNoPackage)
        {
            return InterpretResult(result);
        }

        if (result != ErrorInsufficientBuffer || length == 0)
        {
            return InterpretResult(result);
        }

        var fullName = new StringBuilder((int)length);
        result = GetCurrentPackageFullName(ref length, fullName);
        return result == ErrorSuccess
            ? new PackageIdentityResult(PackageIdentityState.Present, fullName.ToString(), result)
            : InterpretResult(result);
    }

    public static PackageIdentityResult InterpretResult(int result)
    {
        return result switch
        {
            ErrorSuccess => new PackageIdentityResult(PackageIdentityState.Present, null, result),
            AppModelErrorNoPackage => new PackageIdentityResult(PackageIdentityState.Absent, null, result),
            _ => new PackageIdentityResult(PackageIdentityState.Unknown, null, result)
        };
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetCurrentPackageFullName(
        ref uint packageFullNameLength,
        StringBuilder? packageFullName);
}
