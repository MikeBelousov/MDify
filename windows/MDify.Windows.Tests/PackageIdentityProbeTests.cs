using MDify.Windows.Support;
using Xunit;

namespace MDify.Windows.Tests;

public sealed class PackageIdentityProbeTests
{
    [Fact]
    public void NoPackageResult_IsReportedAsAbsent()
    {
        var result = PackageIdentityProbe.InterpretResult(
            PackageIdentityProbe.AppModelErrorNoPackage);

        Assert.Equal(PackageIdentityState.Absent, result.State);
    }

    [Fact]
    public void UnexpectedResult_IsReportedAsUnknownWithoutBlockingStartup()
    {
        var result = PackageIdentityProbe.InterpretResult(5);

        Assert.Equal(PackageIdentityState.Unknown, result.State);
        Assert.Equal(5, result.ErrorCode);
    }
}
