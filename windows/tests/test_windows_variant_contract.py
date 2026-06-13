from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_PROJECT = ROOT / "windows/MDify.Windows/MDify.Windows.csproj"
TEST_PROJECT = ROOT / "windows/MDify.Windows.Tests/MDify.Windows.Tests.csproj"


def test_default_and_target_profiles_are_explicit() -> None:
    project = APP_PROJECT.read_text(encoding="utf-8")

    assert '<MDifyVariant Condition="\'$(MDifyVariant)\' == \'\'">Ocr</MDifyVariant>' in project
    assert "net8.0-windows10.0.17763.0" in project
    assert "net8.0-windows10.0.26100.0" in project
    assert "MDIFY_WINDOWS_OCR" in project
    assert "MDIFY_WINDOWS_LITE" in project
    assert "<WindowsPackageType>None</WindowsPackageType>" in project


def test_windows_ai_dependencies_and_sources_are_lite_only() -> None:
    project = APP_PROJECT.read_text(encoding="utf-8")

    package_reference = (
        '<PackageReference Condition="\'$(MDifyVariant)\' == \'Lite\'" '
        'Include="Microsoft.WindowsAppSDK" Version="2.1.3" />'
    )
    assert package_reference in project
    assert '<ItemGroup Condition="\'$(MDifyVariant)\' == \'Ocr\'">' in project
    for source in (
        r"Services\INativeOcrService.cs",
        r"Services\NativeOcrRoutingClient.cs",
        r"Services\WindowsNativeOcrService.cs",
    ):
        assert f'<Compile Remove="{source}" />' in project
    assert '<None Remove="Package.appxmanifest" />' in project


def test_test_project_tracks_both_variant_profiles() -> None:
    project = TEST_PROJECT.read_text(encoding="utf-8")

    assert "net8.0-windows10.0.17763.0" in project
    assert "net8.0-windows10.0.26100.0" in project
    assert "MDIFY_WINDOWS_OCR" in project
    assert "MDIFY_WINDOWS_LITE" in project
    assert '<Compile Remove="NativeOcrRoutingClientTests.cs" />' in project


def test_lite_manifest_declares_windows_ai_capability() -> None:
    manifest = (ROOT / "windows/MDify.Windows/Package.appxmanifest").read_text(
        encoding="utf-8"
    )

    assert 'MinVersion="10.0.26200.0"' in manifest
    assert 'MaxVersionTested="10.0.26226.0"' in manifest
    assert '<systemai:Capability Name="systemAIModels" />' in manifest


def test_default_routing_and_diagnostic_are_compile_time_split() -> None:
    service = (
        ROOT / "windows/MDify.Windows/Services/ConversionService.cs"
    ).read_text(encoding="utf-8")
    app = (ROOT / "windows/MDify.Windows/App.xaml.cs").read_text(encoding="utf-8")

    assert "#if MDIFY_WINDOWS_LITE" in service
    assert "resolver.CreateClient(WorkerKind.Lite)" in service
    assert "resolver.CreateClient(WorkerKind.Ocr, ocrMode: WorkerOcrMode.Auto)" in service
    assert "#if MDIFY_WINDOWS_LITE" in app
    assert "package_identity=" in app
    assert "ready_state=" in app
    assert "recognition=" in app
    assert "error_type=" in app


def test_lite_readiness_handles_every_windows_ai_terminal_state() -> None:
    app = (ROOT / "windows/MDify.Windows/App.xaml.cs").read_text(encoding="utf-8")
    service = (
        ROOT / "windows/MDify.Windows/Services/WindowsNativeOcrService.cs"
    ).read_text(encoding="utf-8")

    for state in (
        "CapabilityMissing",
        "NotSupportedOnCurrentSystem",
        "DisabledByUser",
        "NotCompatibleWithSystemHardware",
        "OSUpdateNeeded",
    ):
        assert state in app

    assert 'var readyState = "unavailable";' in app
    assert "systemAIModels capability access" in service


def test_no_full_msix_or_sparse_identity_is_required() -> None:
    assert not (ROOT / "windows/identity").exists()
