using MDify.Windows.Models;
using MDify.Windows.Support;
using Xunit;

namespace MDify.Windows.Tests;

public sealed class BuildVariantTests
{
    [Fact]
    public void Current_MatchesCompileTimeVariant()
    {
#if MDIFY_WINDOWS_LITE
        Assert.Equal(AppVariant.Lite, BuildVariant.Current);
#else
        Assert.Equal(AppVariant.Ocr, BuildVariant.Current);
#endif
    }
}
