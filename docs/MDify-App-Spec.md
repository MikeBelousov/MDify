# MDify App Spec

MDify is a native macOS application that converts local documents into Markdown.
It uses Microsoft's MarkItDown Python package, but MDify is not affiliated with
or endorsed by Microsoft.

## Appearance

The app uses a native SwiftUI `NavigationSplitView`.

- Sidebar: queued local files with conversion status.
- Detail: setup screen, empty drop zone, Markdown preview, raw Markdown, and log.
- Toolbar: Add Files, Choose Output Folder, Convert All, Cancel, Copy Markdown,
  Reveal Output.
- Toolbar and menu: Add Folder.
- Settings: Python path, venv state, MarkItDown state, and setup log.
- Queue rows show a small remove button in the upper-left corner on hover.
- Folder-imported queue rows show their relative source path as secondary text.

The app icon is generated from `mdify-icon-clean-markdown-v2.png` after removing
only the edge-connected white corner background so the final `.icns` has
transparent corners.

## Installation

The intended v0 install command is:

```bash
brew install --cask mikebelousov/tap/mdify
```

The first release is unsigned and not notarized. If Gatekeeper blocks launch,
users can run:

```bash
xattr -dr com.apple.quarantine /Applications/MDify.app
open -a MDify
```

## Runtime Requirements

- macOS 14+
- Python 3.10-3.13

MDify does not install Python. It discovers a compatible Python, creates a venv
at `~/Library/Application Support/MDify/Python/venv`, and installs
`markitdown[all]==0.1.6` there. User Python installations are not modified.
Python 3.14 is ignored in v0 because the selected `markitdown[all]` dependency
set is not installable there yet.

## Functional Scope

v0 supports local files and local folders only. It does not accept URLs,
YouTube links, or cloud inputs. Users can add multiple files, add a folder,
select an output folder, convert files sequentially, preview Markdown, copy
Markdown, and reveal output files in Finder. The default output folder is the
user's Downloads directory.

When adding a folder, MDify scans for supported file extensions, skips hidden
entries, `.DS_Store`, symlinks, package directories like `.app`, and unsupported
files. If the folder contains subfolders, MDify asks whether to include
subfolders or only use the top level. Folder output preserves source structure
under `<Output>/<FolderName>/...`.

## Architecture

- `MDify`: SwiftUI executable target.
- `MDifyCore`: testable library for process execution, Python discovery,
  MarkItDown installation, output naming, and conversion queue behavior.
- `ProcessRunner`: subprocess abstraction.
- `PythonEnvironmentManager`: Python 3.10+ discovery, architecture preference,
  and venv creation.
- `MarkItDownInstaller`: pinned MarkItDown installation and version checks.
- `ConversionService`: file queue, sequential conversions, cancellation, logs.
- `OutputFileNamer`: safe `.md` names without silent overwrites.
- `FolderImportService`: local folder scanning and unsupported-entry filtering.
- `ConvertibleFilePolicy`: allowlist of MarkItDown-compatible extensions.

## Intel and Apple Silicon

The release build should be Universal 2 (`arm64` and `x86_64`). Since Python is
not bundled, each user's venv is created locally for their installed Python
architecture. On Apple Silicon, MDify prefers native `arm64` Python.
